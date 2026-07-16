# U-prime / ODLRQ fresh E2 endpoint-semantics authority amendment

Date: 2026-07-16 (Asia/Tokyo)

Authority status: **COMMITTED DOCUMENT FREEZE; NOT AN E2 EXECUTION RESULT**

The anchor is uniquely selected in section 2.  No E2 source, test, runner,
fixture execution, or protected read occurred while authoring these bytes.
Implementation authority becomes active only after this exact committed blob is
pushed and its preregistered section-3 control-red is observed without an extra
failure.

## 1. Objective and unchanged theory boundary

The accepted scientific base is the exact E1 finite-fiber envelope at

```text
commit 6fb35aa229fc60e2220cbb68c1e7fff2ce64f199
tree   b3fc7f21b6420e718eb954be0c1b5affca65d263
subject uprime: qualify exact E1 fiber envelope
```

Its registered dirty E1 lane passed exactly 48 tests.  Candidate and accepted
CI each passed exactly `2600 passed, 8 skipped, 161 deselected`.  E1 remains a
declared finite synthetic result, not an all-germ or production Lean
certificate.

The R6 closeout at `03f7b81fed7cb1f65f35cbccfab9c110cc544e39`
correctly stopped before E2 because four public endpoint semantics were not
unique: parent-envelope restriction, the retained/memory split, weighted norm
and block orientation, and the pre-gate candidate universe.  This document
answers only those four questions and freezes the minimum execution architecture
needed to test them later.  It does not reopen the 2026-07-10 theory review,
change the finite-horizon formulas, claim infinite-time stability, or execute
E2.

The exact inherited formulas remain

```text
M_[n,n+h) = M_(n+h-1) ... M_n
M_n^T w_(n+1) <= theta_n w_n,  w_n > 0
||M_[n,n+h)||_(1,w) <= product_(j=n)^(n+h-1) theta_j

R_h = sum_(k=0)^(h-1) M_PQ (M_QQ)^k M_QP.
```

All comparisons and all stored endpoint values are reduced exact rationals.
A float log-pressure may be computed only after the exact decision and is never
an input to a pass bit, support token, or safety claim.

## 2. Fresh phase, R13 boundary, and unique anchor

R7--R13 never created or executed an E2 scientific endpoint.  Their accepted
failure-closeout commits add only failure documents relative to E1; code,
tests, tools, and workflow are byte-identical between accepted E1 `6fb35aa...`
and R13 closeout `9f45fc7...`.

R13 ended at

```text
commit 9f45fc746d76eea5e3daf1bb44b449f6d3d8e542
tree   8d3616727accf12c5a535222a7c2d355b4e07b96
status FAILED_CLOSED_EXTERNAL_CAPTURE_CALIBRATION
scientific execution count 0
fourth control repair licensed false
```

Its external wrapper read a capture file while its own incompatible write-side
stream remained open.  R13 did not adjudicate whether a descendant retained
stderr, and this document must never report that hypothesis as passed or
failed.  No R13 wrapper, supervisor, calibration, failed worktree, identity,
guard, or monolithic runner is changed, imported, rerun, or repaired here.

The unique scientific parent is accepted E1
`6fb35aa229fc60e2220cbb68c1e7fff2ce64f199`.  R6--R13 are cited read-only
evidence outside the new scientific branch ancestry; the new phase contains no
R13 control repair.  This is the base commit named by directive
`FABLE-20260716-0001`.

Static inspection of the immutable current identity test established a further
constraint before this amendment was committed: any new document-only row
after accepted E1 is outside the frozen E2 allowlist and fails
`test_u24_b0_anchor_contiguous_budget_and_terminal_topology` at
`_classify_build_rows` line 534.  Likewise, a new dedicated runner path is not
in that E2 allowlist.  Therefore requiring the authority document or new runner
in the scientific first-parent ancestry while also requiring ordinary green CI
is impossible without a forbidden identity/guard repair.

The unique no-repair topology is consequently a content-addressed sibling
split:

```text
accepted E1 6fb35aa
  |-- authority side ref: one document-only authority commit
  `-- local scientific source commit: one exact four-path E2 semantic commit

authority commit (first parent) + semantic commit (second parent)
  `-- runner-control carrier merge: tree = authority tree + runner only
        `-- success/failure closeout side ref: one document-only child

semantic commit
  |-- build ref after a passing one-shot
  `-- accepted ref fast-forward target after green build CI.
```

The authority document side ref is expected to have exactly the one known
topology-control failure and no E2 execution.  The four-path semantic commit is
a direct child of accepted E1, embeds the final authority commit and document
blob SHA literally, and is the only branch required to pass scientific
candidate/accepted CI.  Before the one shot the semantic commit exists locally
without a branch ref, then is
made remotely reachable only as the second parent of a runner-control carrier
merge whose checked-out tree contains the authority document and runner but no
E2 source or test.  Thus runner-control CI cannot execute the scientific
endpoint.  That merge is pushed immutably before the one shot and never enters
the accepted ref.  The reports and terminal closeout bind all three
commits/trees/blobs.

On 2026-07-16 the user explicitly directed Codex to proceed autonomously rather
than treat Fable as an approval gate and to decide whether later trajectory
corrections should be adopted.  After static proof that the requested green
authority ancestry is impossible under the immutable topology test, Codex
formally **partially rejects** only that unattainable clause of
`FABLE-20260716-0001` under the user's direct authority.  Dated bridge ACK
`CODEX-20260716-0005` precedes publication of this amendment.  Every scientific endpoint, the no-
fourth-control-repair rule, protected-read prohibition, and no-E2-before-freeze
rule remains adopted.  This is an explicit protocol decision, not an
uncommitted document bootstrapping its own license.

R13 CI run `29470878080`, job `87533665818`, is red at the inherited
identity-topology test with exactly
`1 failed, 2599 passed, 8 skipped, 161 deselected`.  Making R13 the parent would
require either prohibited topology wiring or a green-CI waiver; neither is
licensed.  That rejected alternative is recorded here to prevent a future
reviewer from silently reintroducing it.

Under this fresh topology, the phase is not R14 and is not a continuation
of the external-capture repair sequence.  It is a new endpoint-definition
phase authorized after R13 stopped.  R13 remains immutable failure evidence.

## 3. Dated result-red-CI clarification

### 2026-07-16 clarification for future readers

The immutable U05 result-publication commit
`cc91a4181a9f87ec10f11727ed787eb7149f955a` has red Actions run
`29166670576`, job `86580832840`.  The dated audit attributes that badge to a
guard shallow-history design omission, not a probe, prerequisite,
artifact-integrity, or scientific-endpoint failure.  The exact scientific
candidate `3bb3408afc50a08307cff2c9b1906a299739dfb5` passed green candidate
CI run `29166073728`, job `86579287017`.  The red result badge must not be read
as failed science.  The audit authority for that attribution is immutable
commit `628d3cc64af2531da3a527bad335d9e5158294a7`.

The R13 red run described in section 2 is a separate inherited
identity-topology failure in
`tests/test_uprime_u2_u4_development.py::test_u24_b0_anchor_contiguous_budget_and_terminal_topology`
with the failing call chain at lines `1003 -> 648`.  It also contains no E2
result.  Neither red badge may be used as evidence for or against the upper
mathematical program.

### 2026-07-16 sibling-side-ref control-red rule

The authority, runner-control, and terminal-closeout refs introduced here are
deliberately outside the accepted scientific first-parent line.  Under the
immutable current identity test, each contains a path that the old construction
bundle never registered and is therefore expected to show the same single
topology-control failure.  That red is preregistered control evidence, not an E2
endpoint result.  The exact run/job and sole failing node are recorded after
each push.  Any additional failed node, an E2 test on the authority ref, or a
scientific failure on the four-path build/accepted ref is not covered by this
adjudication and stops the phase.

The topology-conditional hosted expectations are frozen as follows:

| checked-out ref/tree | E2 nodes present | admissible CI observation |
|---|---:|---|
| authority side ref | no | exactly 1 topology failure + 2599 pass, 8 skip, 161 deselect |
| runner carrier-merge side ref | no | exactly 1 topology failure + 2599 pass, 8 skip, 161 deselect |
| pre-semantic failure closeout child of authority | no | exactly 1 topology failure + 2599 pass, 8 skip, 161 deselect |
| post-semantic/pre-runner two-parent failure carrier `[authority,semantic]` with authority+closeout tree | no | exactly 1 topology failure + 2599 pass, 8 skip, 161 deselect |
| post-carrier success/failure closeout child of runner | no | exactly 1 topology failure + 2599 pass, 8 skip, 161 deselect |
| semantic build or accepted ref | yes | exactly 2610 pass, 8 skip, 161 deselect for acceptance; any red is scientific/integration evidence and stops |

Thus a scientific build failure is copied into a control-side closeout but is
never relabeled as its closeout tree's single topology failure.  The closeout
CI observation and the bound scientific CI observation remain separate fields.

The terminal closeout cannot contain its own future Actions identity.  Its sole
durable post-closeout sink is one create-new UTF-8 canonical JSON record under
`%USERPROFILE%\Desktop\codex_claude_bridge\terminal_observations\`, named
`u24_e2_closeout_ci__<full-40-hex-closeout-commit>.json`.  The deterministic
full-SHA path must be absent before exclusive creation; a pre-existing file or
second creation attempt is a terminal mismatch, not another record.  It has exact keys

```text
schema_version, created_at, phase, closeout_ref, closeout_commit,
closeout_tree, closeout_document_blob, actions_run_id, actions_job_id,
workflow_head_sha, passed, failed, skipped, deselected,
failing_node_ids, disposition.
```

The schema is `codex-fable-terminal-ci-observation-v1`; the file is exclusively
created through `FileStream`, durably `Flush(true)`ed, closed, reopened, strict-
parsed, and rehashed once, then never edited, replaced, or deleted.  The mutable bridge state
may point to it but is not the evidence authority.  Exact expected control-red
uses disposition `U24_E2_CLOSEOUT_CI_OBSERVED`; any count/node/SHA mismatch uses
`U24_E2_CLOSEOUT_CI_OBSERVATION_MISMATCH` and stops without a repository
correction.  This one terminal observation is not a scientific result store or
multi-entry ledger.

## 4. Immutable accepted-E1 dependency and additive-only E2 boundary

The following accepted E1 blobs are immutable dependencies:

| path | Git blob |
|---|---|
| `lean_rgc/odlrq/quotient_generator.py` | `1e1576ad1f51ebf667bc55d159048c0ae6587524` |
| `lean_rgc/odlrq/envelope.py` | `0618f603b86eba3c61c9fb2e15c4edaacce44a14` |
| `lean_rgc/odlrq/__init__.py` | `f97272d5de222fb555a78639d66eb89e77e63d86` |

Fresh E2 may import their public exact types but may not edit, monkey-patch,
rebind, wrap, subclass, replace, or append exports to those files.  E2 public
types are public from their defining modules; top-level package re-export is
not required.  If implementation would require an accepted E1 byte to change,
the phase stops before E2 execution with
`U24_E2_ACCEPTED_E1_DEPENDENCY_BLOCKED`.

New E2 wires use exact key sets and do not use legacy permissive
`metadata.extra` parsing.  Every retained authority is exact-type checked,
revalidated, and freshly rederived at serialization time.

## 5. Common matrix convention and the fixed declared endpoint

The only matrix convention is

```text
column-vector action
matrix row    = target coordinate
matrix column = source coordinate
basis tag     = target_row_source_column_v1.
```

For a typed E1 parent envelope `E`, let its complete ordered source and target
block bases be `S` and `T`, and define

```text
M_E[i,j] = E.majorant_for(target_block=T[i], source_block=S[j]).
```

The fixed abstract coordinate basis is

```text
I = [OPEN_0, OPEN_1, CLOSED, SINK].
```

A `SourceTargetCoordinateIdentification` supplies exhaustive role/response-
derived bijections `phi_s : I -> S` and `phi_t : I -> T`.  Coordinate rows are
stored in declared `I` order; native E1 block indices may be nonmonotone and
are never reordered to imitate `I`.  It binds
the parent envelope full-wire digest, both E0 generator digests, reachable
domains, verified partitions, block orders, block member-set digests,
coordinate roles, completeness witnesses, and positive-weight authorities.
Dimension equality alone is invalid.  Raw source and target IDs are not
identified with each other.

The abstract full matrix is

```text
M^I[i,j] = M_E[phi_t(i), phi_s(j)].
```

The fixed endpoint uses five full parents:

```text
M0_full = [[1,   2, 0, 0],
           [0, 1/2, 0, 0],
           [0,   0, 0, 0],
           [0,   0, 0, 0]]

M1_full = [[1/2, 0, 0, 0],
           [3,   1, 0, 0],
           [0,   0, 0, 0],
           [0,   0, 0, 0]]

Mret_full = [[0,   2, 0, 0],
             [3, 1/2, 0, 0],
             [0,   0, 0, 0],
             [0,   0, 0, 0]]

Nonnormal_full = [[1, 10, 0, 0],
                  [0,  1, 0, 0],
                  [0,  0, 0, 0],
                  [0,  0, 0, 0]]

Nilpotent_full = [[0, 1, 0, 0],
                  [0, 0, 0, 0],
                  [0, 0, 0, 0],
                  [0, 0, 0, 0]].
```

The source and target exact positive quotient weights are `[1,1,1,1]` in
abstract order for this endpoint.  Every one of the twelve cells whose row or
column touches `CLOSED` or `SINK` is replayed from the E1 parent and must be
exact zero.  Zeros may not be inserted after restriction.

The two diagnostic parents are mandatory: `Nonnormal_full` tests transient
gain, and `Nilpotent_full` tests finite extinction.  They do not create an
infinite-horizon or spectral claim.

### 5.1 Complete canonical E1 fixture derivation

The five displayed matrices are not caller-supplied envelope data.  The future
test module contains one private literal fixture builder whose only internal
selector is one of

```text
[M0, M1, MRET, NONNORMAL, NILPOTENT].
```

It constructs the complete E1 authorities through the accepted public E0/E1
builders.  The raw fixture is frozen as follows; no generated suffix, random
value, caller mapping, or alternative payload spelling is permitted:

```text
coordinate_names = ["e2_coordinate"]
source environment_digest = "53" repeated 32 times
target environment_digest = "54" repeated 32 times

source action:
  id      = "u24_e2_source_a"
  payload = {"kind":"action","name":"u24_e2_source_a"}
target action:
  id      = "u24_e2_target_a"
  payload = {"kind":"action","name":"u24_e2_target_a"}

source states, in construction order:
  ("u24_e2_source_open0_a", OPEN,   0)
  ("u24_e2_source_open0_b", OPEN,   0)
  ("u24_e2_source_open1",   OPEN,   1)
  ("u24_e2_source_closed",  CLOSED, 2)
  ("u24_e2_source_sink",    SINK,   3)
target states, in construction order:
  ("u24_e2_target_open0",  OPEN,   0)
  ("u24_e2_target_open1",  OPEN,   1)
  ("u24_e2_target_closed", CLOSED, 2)
  ("u24_e2_target_sink",   SINK,   3).
```

Each state payload is exactly
`{"kind":"state","name":<the exact state ID>}`.  Each state has one
self-transition under its side's sole action.  Seed IDs are exactly the OPEN
state IDs in the construction order above.  Each side is built by
`build_synthetic_finite_snapshot`, `admit_synthetic_finite_snapshot`,
`refine_exact_partition`, `verify_exact_partition`, then
`build_exact_quotient_coordinate_generator`.  Thus `OPEN_0` on the source has
two raw members, while every other declared coordinate has one.  The abstract
coordinate order is the declared `I`; it is not inferred from numeric block
indices.

All raw source and target member weights are exactly one.  The primary source
law is

```text
source OPEN_0: open0_a = 1/3, open0_b = 2/3
source OPEN_1, CLOSED, SINK: the sole member = 1.
```

For a selected displayed matrix `A`, the sparse signed coefficient table is
generated in target-coordinate-major, then source-member construction order.
Only nonzero rows are emitted, and the rule is exactly

```text
K(target OPEN_i, source open0_a) =  A[i,OPEN_0]
K(target OPEN_i, source open0_b) = -A[i,OPEN_0]
K(target OPEN_i, source open1)   =  A[i,OPEN_1]
all coefficients touching source or target CLOSED/SINK = 0 and are omitted.
```

The layer, both positive-weight authorities, the primary law, both
completeness witnesses, and the envelope are then built by
`declare_synthetic_transfer_layer`, `make_positive_fiber_weights`,
`make_exact_finite_fiber_law`, `certify_fiber_completeness`, and
`build_fiber_envelope`.  This signed table makes every E1 candidate load and
majorant equal the displayed nonnegative matrix while keeping cancellation out
of the safety proof.

The law-independence test rebuilds only the `M0` envelope with the same exact
generators, layer, weights, and completeness witnesses and the alternate law

```text
source OPEN_0: open0_a = 2/3, open0_b = 1/3
source OPEN_1, CLOSED, SINK: the sole member = 1.
```

This is a diagnostic provenance variant, not a sixth endpoint parent.  Its
parent full-wire digest and signed compressed coefficients change; its
candidate loads, majorants, coordinate core, restriction core, and
law-independent theorem-core digest must not change.

## 6. Unique public parent-envelope restriction

The retained ordered basis and its complement are exactly

```text
J  = [OPEN_0, OPEN_1]
Jc = [CLOSED, SINK].
```

`EnvelopeRestrictionWitness` is constructed only from an exact typed
`FiberEnvelope`, its exact typed `SourceTargetCoordinateIdentification`, and
the fixed endpoint builder.  It stores and rederives

```text
parent_envelope_sha256
coordinate_identification_sha256
full_coordinate_ids = I
retained_coordinate_ids = J
complement_coordinate_ids = Jc
restricted_matrix = M^I[J,J]
restricted_matrix_sha256
restricted_source_weights = w_source[J]
restricted_target_weights = w_target[J]
restricted_source_weights_sha256
restricted_target_weights_sha256
omitted_cell_count = 12
omitted_cells_sha256
replayed_cell_count = 16
replay_pass = true
```

The explicit restricted weight vectors fix a gap in the unaccepted R7/R8
design precedent: a matrix without its rederived source and target weights is
not an admissible restriction witness.

The public function is uniquely

```python
build_e2_envelope_restriction(
    *,
    envelope: FiberEnvelope,
    identification: SourceTargetCoordinateIdentification,
) -> EnvelopeRestrictionWitness
```

`EnvelopeRestrictionWitness.from_dict(value, *, envelope, identification)`
requires those retained exact authorities and compares the complete freshly
rederived canonical wire.  A public raw constructor, caller-supplied `2 x 2`
matrix, sparse spelling, reordered retained basis, implicit terminal zero,
caller-supplied restricted weight, or wire-only reconstruction is forbidden.

The fixed open restrictions are

```text
M0        = [[1,   2], [0, 1/2]]
M1        = [[1/2, 0], [3,   1]]
Mret      = [[0,   2], [3, 1/2]]
Nonnormal = [[1,  10], [0,   1]]
Nilpotent = [[0,   1], [0,   0]].
```

## 7. Lifting-uniform finite safety core

`LiftingUniformSafetyCertificate` is tied to one
`EnvelopeRestrictionWitness`.  It replays every complete finite E1 candidate
load and majorant.  Its exact law scope is

```text
all_exact_nonnegative_block_probability_laws_on_complete_declared_source_blocks_v1.
```

For each complete source block and exact law `p_s >= 0`, `sum_s p_s = 1`, the
checker independently derives

```text
|sum_s p_s signed_load_s|
  <= sum_s p_s absolute_load_s
  <= max_s absolute_load_s
  = E1 majorant.
```

The law-independent theorem-core digest is the uppercase SHA-256 of canonical
contract bytes for exactly

```text
{
  "schema_version":"odlrq.e2.lifting_uniform_theorem_core.v1",
  "endpoint_id":"u24_e2_declared_square_endpoint_v1",
  "parent_id":<fixed parent ID>,
  "basis_convention":"target_row_source_column_v1",
  "layer_sha256":<rederived declared-layer digest>,
  "source_generator_sha256":<rederived digest>,
  "target_generator_sha256":<rederived digest>,
  "source_weights_sha256":<rederived digest>,
  "target_weights_sha256":<rederived digest>,
  "source_completeness_sha256":<rederived digest>,
  "target_completeness_sha256":<rederived digest>,
  "coordinate_core_sha256":<law-free coordinate-core digest>,
  "restriction_core_sha256":<law-free restriction-core digest>,
  "ordered_candidate_loads":<all 20 exact candidate-load rows>,
  "majorant_matrix":<the full exact 4 x 4 matrix>,
  "scope":"all_exact_nonnegative_block_probability_laws_on_complete_declared_source_blocks_v1"
}.
```

It explicitly excludes `parent_envelope_sha256`, the full identification and
restriction wire digests, `source_law_sha256`, every signed compressed
coefficient, every absolute compressed coefficient, and every source-law
probability.  Those are outer provenance only and may not be substituted for
candidate loads or used as a safety argument.  Rebuilding the same finite
complete data with the alternate exact law in section 5.1 must preserve the
theorem-core digest while changing the parent full-wire digest and the outer
certificate full-wire digest.

This certificate is uniform only over the declared finite simplex.  It says
nothing about unknown states, incomplete fibers, floating or learned laws, or
an infinite domain.

## 8. Unique P/Q split and finite return memory

`ResolvedMemorySplit` is defined over `J`, never over raw E0 IDs or a supplied
submatrix.  Both sides are inherited-order subsequences, nonempty, disjoint,
and exhaustive:

```text
P = [OPEN_0]
Q = [OPEN_1]
P != empty
Q != empty
P intersection Q = empty
P union Q = J.
```

For any ordered `A,B` subsets, the notation is fixed as

```text
M_AB = rows A, columns B, hence M_AB maps B -> A.
```

Therefore

```text
M_PP = rows P, columns P
M_PQ = rows P, columns Q
M_QP = rows Q, columns P
M_QQ = rows Q, columns Q.
```

For `Mret`:

```text
M_PP = [0]
M_PQ = [2]
M_QP = [3]
M_QQ = [1/2]
h = 3.
```

Accepted E1 deliberately uses distinct source and target generators.  A
coordinate identification is not a `FrameMorphism`, so repeated raw-domain
application of one E1 transfer is not available.  This endpoint therefore
freezes the limited iteration tag

```text
stationary_reuse_of_restricted_abstract_majorant_v1.
```

Under that tag alone, the restricted matrix is transported to the one declared
abstract coordinate basis and reused as a stationary finite synthetic
majorant.  It is admissible only when ordered source and target abstract IDs
are identical and the rederived restricted source and target weight vectors
are elementwise identical.  Their role-tagged provenance digests are expected
to differ and are not compatibility witnesses.  It is not a raw-generator cocycle or compiler
transport.  Production iteration later requires exact target-to-next-source
authority or a separately proved transport/`FrameMorphism`.

`ReturnMemoryBound` sequentially rederives and stores `M_QQ^k` for
`k=0,...,h-1` with power zero equal to the exact identity on `Q`, every term,
the exact finite sum, operation count, split/restriction/weight digests, and
`finite_only=true`:

```text
R_3 = 2*1*3 + 2*(1/2)*3 + 2*(1/2)^2*3
    = 6 + 3 + 3/2
    = 21/2.
```

The `P -> P` source and target weights are rederived as `[1]`, so the exact
weighted norm is `21/2`.  The fixture intentionally has `M_PP=0` and
`R_3>0`: a direct observational zero does not justify pruning a memory-active
coordinate.

No inverse, resolvent, spectral-radius bound, decay rate, geometric tail,
`h -> infinity`, or horizon-uniform statement is serializable.

## 9. Unique weighted norm, cocycle compatibility, and P2 scope

For a nonnegative matrix `M : S -> T` with exact positive reduced rational
weights `w_S,w_T`, the only weighted norm is

```text
||M||_(w_T <- w_S,1)
  = max over source columns j
      (sum over target rows i of w_T[i] * M[i,j]) / w_S[j].
```

No zero, negative, float, missing, caller-reordered, or stale weight is
admissible.  `CocycleCertificate` requires exact equality of the ordered
abstract intermediate basis and exact equality of the previous target-weight
coordinate IDs and `R` values with the next source-weight coordinate IDs and
`R` values.  Their role-tagged provenance digests are not compared.  Sharing only a dimension
is insufficient.  This fixed endpoint has no raw target-generator = next
source-generator authority and therefore uses exactly the composition tag

```text
declared_abstract_coordinate_composition_v1.
```

It certifies multiplication only after transport into the common declared
abstract coordinate basis.  It does not certify raw-layer composition,
generator equality, a `FrameMorphism`, or compiler transport.  The product
order is exactly

```text
rightmost_earliest_M_hminus1_dotdot_M0_v1
M_[0,h) = M_(h-1) ... M_0.
```

Each layer checks `M_j^T w_(j+1) <= theta_j w_j` componentwise and then checks
the exact product norm against `product theta_j`.

The two non-substitutable channel enums remain

```text
P1_BRANCHING_ADJUSTED
P2_BRANCHING_ADJUSTED.
```

For this fixed synthetic endpoint their mandatory derivation fields are,
respectively,

```text
identity_positive_majorant_v1
entrywise_square_no_cross_terms_synthetic_v1.
```

The inherited P2 enum name is not a theorem that entrywise squaring closes a
general second-moment branching channel.  The exact field and mandatory
nonclaim prevent that overstatement.

The independently rederived fixed goldens are

```text
P1:
  w0 = w1 = w2 = [1,1]
  theta = [5/2, 7/2]
  M1 M0 = [[1/2, 1], [3, 13/2]]
  weighted norm = 15/2
  theta product = 35/4
  15/2 <= 35/4

P2:
  layer matrices = entrywise squares of the P1 layers
  w0 = w1 = w2 = [1,1]
  theta = [17/4, 37/4]
  M1^(entry 2) M0^(entry 2) = [[1/4, 1], [9, 145/4]]
  weighted norm = 149/4
  theta product = 629/16
  149/4 <= 629/16.
```

## 10. Unique pre-gate candidate universe and binding selector

`CandidateUniverseManifest` is sealed before the threshold is read and its
builder accepts no threshold, decision, filtered row list, denominator, or
support argument.  This phase exposes no generic caller-supplied candidate-row
builder.  The fixed builder derives exactly the canonical ordered universe
`[c0,c1,c2]` from typed bound authorities:

```text
c0:
  source membership = OPEN_0 singleton
  bound authority = M0[target=OPEN_0, source=OPEN_0] = 1
  utility = 1

c1:
  source membership = OPEN_0 singleton
  bound authority = M1[target=OPEN_1, source=OPEN_0] = 3
  utility = 9

c2:
  source membership = OPEN_1 singleton
  bound authority = M0[target=OPEN_0, source=OPEN_1] = 2
  utility = 4.
```

Each row binds the candidate ID and payload digest, exact typed membership,
parent E1 envelope, coordinate identification, restriction, lifting-uniform
safety core, target/source coordinate IDs, exact utility, and rederived bound.
The payload digest is derived from exactly one of the following literal
canonical objects; no free-form payload is admitted:

```text
{"schema_version":"odlrq.e2.synthetic-candidate.v1",
 "candidate_id":"c0","declared_action_id":"E2_SYNTHETIC_C0"}
{"schema_version":"odlrq.e2.synthetic-candidate.v1",
 "candidate_id":"c1","declared_action_id":"E2_SYNTHETIC_C1"}
{"schema_version":"odlrq.e2.synthetic-candidate.v1",
 "candidate_id":"c2","declared_action_id":"E2_SYNTHETIC_C2"}.
```

The membership-to-bound relation is explicit: membership is in the singleton
source coordinate named by the bound authority.  A mere unrelated
`DomainMembershipWitness` digest is insufficient.

`pre_gate_complete=true` means complete only relative to this literal declared
three-row synthetic universe.  It is not a proof that all possible proof-search
candidates were registered, and it is not a production selective-evaluation
solution.

Ungated utility order is derived by `(-utility, candidate_id)`.  Only after the
manifest is sealed does the gate use the internally fixed exact threshold `2`,
comparator `exact_rational_less_equal_v1`, ordered passed `[P1,P2]` cocycle
authorities, and the exact finite return-memory authority.  It accepts no
threshold argument.  It emits exactly one decision row per manifest row:

```text
valid bound <= threshold  ACCEPT
valid bound > threshold   REJECT.
```

Every row in this v1 fixed manifest is fully typed and valid before sealing.
Missing, malformed, stale, or substituted evidence raises
`StrictContractError` before a decision table or token exists; it is not
silently converted to a decision.  Consequently `ABSTAIN` and
`ABSTAIN_NO_CERTIFIED_SUPPORT` are deliberately **not constructible in this
schema**.  They remain names reserved for a future generic selective-evaluation
schema that would require its own amendment, explicit evidence-status variant,
coverage endpoint, and public result type.  Rejects never leave the denominator
and equality is accepted.  The exact endpoint is

```text
manifest universe        [c0,c1,c2]
coverage denominator     3
ungated utility ranking  [c1,c2,c0]
accepted support         [c0,c2]
rejected                 [c1]
coverage                 2/3
gated utility ranking    [c2,c0]
ranking_changed          true
```

`ranking_changed` is defined as

```text
ungated_top_candidate_id != gated_top_candidate_id,
```

not merely unequal list lengths or orderings.  The fixed top changes from
`c1` to `c2`, so the gate is reachable, nonempty, and ranking-binding.

`CertifiedSupportToken` can be created only inside the gate from the complete
decision table.  It binds all manifest and certificate authorities, every
decision row, denominator, numerator, rankings, rejected IDs, the exact empty
`abstained_candidate_ids` array, support IDs, comparator, threshold, and
invalidation digest.  Because this fixed gate has support `[c0,c2]`, the public
return type is exactly `CertifiedSupportToken`, never `None` or a status tuple.
Future ME0 requires exact type
`CertifiedSupportToken` and nonempty support and may neither create nor enlarge
support.  Its only failure fallback is ascending canonical candidate ID within
the already certified support.

## 11. Frozen public types, API placement, and strict validation order

Exactly these eight public types are admitted; they are value/certificate
types, not a new quotient or evidence subsystem:

```text
lean_rgc.odlrq.certificates.SourceTargetCoordinateIdentification
lean_rgc.odlrq.certificates.EnvelopeRestrictionWitness
lean_rgc.odlrq.certificates.LiftingUniformSafetyCertificate
lean_rgc.odlrq.certificates.ResolvedMemorySplit
lean_rgc.odlrq.certificates.CocycleCertificate
lean_rgc.odlrq.certificates.ReturnMemoryBound
lean_rgc.odlrq.selection.CandidateUniverseManifest
lean_rgc.odlrq.selection.CertifiedSupportToken
```

They use the accepted E1 sealed-type pattern:

- exact class equality, never `isinstance` or subclasses;
- frozen sealed objects with no public raw constructor;
- named builders require retained exact typed authorities;
- strict `from_dict` requires the same authorities;
- `to_dict` freshly rederives the wire rather than serializing mutable cached
  visible fields;
- canonical UTF-8 JSON, exact key sets, uppercase SHA-256, ordered arrays, and
  reduced `ExactRational` values;
- no bool-as-int, float exact field, unknown key, silent truncation, sorting or
  normalization repair, implicit zero, alternate sparse wire, stale digest,
  or property/full-wire digest substitution.

Validation order is fixed:

```text
1. exact external key/type/cardinality preflight over the already-decoded value
2. bounded structural walk before any parser-owned proportional wire allocation
3. bounded accepted-E1 authority type/digest revalidation through public APIs
4. derive E2 dimensions/counts and check all E2 work/allocation caps before any
   E2-proportional container
5. complete independent mathematical rederivation
6. canonical-byte equality with the supplied wire
7. construction seal and final immutable value.
```

### 11.1 Canonical digest domain and hard caps

`R` below means the existing exact three-key `ExactRational` wire
`{schema_version,numerator,denominator}` in reduced canonical form.  `Mat(r,c)`
means an exact outer array of `r` row arrays, each containing exactly `c` `R`
values.  All SHA fields are uppercase SHA-256 of
`canonical_contract_bytes`; no wire contains its own full-wire SHA.  For each
public type `T`, the property named `<type>_sha256` is computed only as
`SHA256(T.to_dict())` and is never accepted from a caller.

Every one of the eight public wires and every property/core preimage that has
an `endpoint_id` key uses exactly
`u24_e2_declared_square_endpoint_v1`.  No builder accepts or derives another
endpoint ID.

The hard preflight caps are literal:

```text
MAX_E2_CANONICAL_WIRE_BYTES       = 1,048,576
MAX_E2_NESTING_DEPTH              = 12
MAX_E2_STRUCTURAL_NODES           = 4,096
MAX_E2_UTF8_SCALAR_BYTES          = 262,144
MAX_E2_COORDINATES                = 4
MAX_E2_RAW_SOURCE_MEMBERS         = 5
MAX_E2_RAW_TARGET_MEMBERS         = 4
MAX_E2_MATRIX_CELLS               = 16
MAX_E2_CANDIDATE_LOAD_ROWS        = 20
MAX_E2_HORIZON                    = 3
MAX_E2_RETURN_TERMS               = 3
MAX_E2_DECLARED_CANDIDATES        = 3
MAX_E2_DECISION_ROWS              = 3
MAX_E2_DERIVATION_WORK_UNITS      = 256.
```

Every `from_dict` entry receives an already-decoded Python `dict`; it therefore
does not and cannot claim to bound an upstream JSON decoder's allocation.  It
first performs a non-copying, depth-bounded structural walk of that existing
object, rejects a noncanonical key/type/cardinality shape, derives a canonical-
wire byte count no larger than `MAX_E2_CANONICAL_WIRE_BYTES`, and only then
allocates parser-owned proportional rows or canonical serialization buffers.
The walk uses object-identity cycle detection, stops before visiting structural
node 4,097 or depth 13, and incrementally counts the exact UTF-8 canonical JSON
escaping of each scalar, stopping before scalar byte 262,145 or total byte
1,048,577; it does not construct a speculative full JSON string to learn its
size.
Accepted E0/E1 authorities are then revalidated under their own already-
accepted caps; all derived E2 counts are checked before an E2-proportional
container is allocated.  These constants are private module constants, not
caller parameters.

`MAX_E2_DERIVATION_WORK_UNITS` is an up-front checked upper bound, not an
elapsed-time surrogate.  A work unit is one scheduled bounded row/cell/term
visit in the named builder.  With `S=5` source members, `T=4` target members,
`I=4` coordinates, `L=20` candidate-load rows, `H=3` horizon terms, `C=3`
candidates, and `R=3` return terms, the only admitted schedules are

```text
identify       9 + S + T + I + I^2             = 38
restriction    L + I + I^2 + I                  = 44
safety         L + I^2 + I + I + 1              = 45
split          I^2 + I                          = 20
cocycle        2*I^2 + 3*I + I                  = 48
return         H*(I^2 + I) + R                  = 63
manifest       C*(L + I + 1)                    = 75
gate           C + C + R + 1                    = 10.
```

Each builder computes its corresponding formula with checked integer
arithmetic from already validated dimensions before entering a proportional
loop or allocating its output.  Any overflow, different schedule, or value over
256 fails before authority is constructed.  The table is deliberately
conservative; it does not assert that a Python exact-rational primitive has
constant wall time.

### 11.2 Literal public wires

The exact top-level key sets and nested row key sets are as follows.  The order
shown is the semantic canonical array order; JSON object key order remains the
one produced by canonical contract bytes.

**`SourceTargetCoordinateIdentification`**, schema
`odlrq.e2.source-target-coordinate-identification.v1`, has exactly:

```text
schema_version, endpoint_id, parent_id, source_law_variant, basis_convention,
parent_envelope_sha256, layer_sha256,
source_generator_sha256, target_generator_sha256,
source_weights_sha256, target_weights_sha256, source_law_sha256,
source_completeness_sha256, target_completeness_sha256,
full_coordinate_ids, source_block_count, target_block_count,
coordinate_rows, coordinate_core_sha256, verification_disposition.
```

`coordinate_rows` has four rows in `I` order, each with exactly

```text
coordinate_id, coordinate_role, source_block_index, target_block_index,
source_member_ids, target_member_ids,
source_member_set_sha256, target_member_set_sha256,
source_weight, target_weight.
```

Roles are exactly `RETAINED_OPEN`, `TERMINAL_CLOSED`, `TERMINAL_SINK` in the
order `[RETAINED_OPEN,RETAINED_OPEN,TERMINAL_CLOSED,TERMINAL_SINK]`.
Member-ID arrays are the exact frame order, not sorted repairs.  Each member-set
digest hashes exactly
`{schema_version:"odlrq.e2.member-set-property.v1",side,coordinate_id,members}`,
where `side` is `SOURCE` or `TARGET` and `members` is the exact array of
`{member_id,member_sha256}` rows.  Each
coordinate weight is the common raw weight rederived for every member in that
block; unequal within-block weights fail this fixed endpoint.  The
`coordinate_core_sha256` preimage has exactly

```text
schema_version="odlrq.e2.coordinate-core.v1", endpoint_id,
basis_convention, layer_sha256, source_generator_sha256,
target_generator_sha256, source_weights_sha256, target_weights_sha256,
source_completeness_sha256, target_completeness_sha256,
full_coordinate_ids, coordinate_rows.
```

`source_law_variant` is exactly `PRIMARY` for every fixed parent or
`ALTERNATE_M0_DIAGNOSTIC` for the sole section-5.1 alternate envelope.  It
excludes parent-envelope, source-law digest, and law-variant label from the
coordinate core.

**`EnvelopeRestrictionWitness`**, schema
`odlrq.e2.envelope-restriction.v1`, has exactly:

```text
schema_version, endpoint_id, parent_id, source_law_variant, basis_convention,
parent_envelope_sha256, coordinate_identification_sha256,
coordinate_core_sha256, full_coordinate_ids, retained_coordinate_ids,
complement_coordinate_ids, full_matrix, restricted_matrix,
restricted_matrix_sha256, restricted_source_weights,
restricted_source_weights_sha256, restricted_target_weights,
restricted_target_weights_sha256, omitted_cells, omitted_cells_sha256,
omitted_cell_count, replayed_cell_count,
restriction_core_sha256, replay_pass, verification_disposition.
```

`full_matrix=Mat(4,4)`, `restricted_matrix=Mat(2,2)`, and each weight array has
two `R` values.  `omitted_cells` has exactly twelve rows in full-matrix
row-major order after excluding `J x J`; each row has exactly
`{target_coordinate_id,source_coordinate_id,value}` and value zero.  The
`restriction_core_sha256` preimage has exactly

```text
schema_version="odlrq.e2.restriction-core.v1", endpoint_id, parent_id,
basis_convention, coordinate_core_sha256, full_coordinate_ids,
retained_coordinate_ids, complement_coordinate_ids, full_matrix,
restricted_matrix, restricted_matrix_sha256, restricted_source_weights,
restricted_source_weights_sha256, restricted_target_weights,
restricted_target_weights_sha256, omitted_cells, omitted_cells_sha256,
omitted_cell_count, replayed_cell_count.
```

The four nested property preimages are literal:

```text
restricted_matrix_sha256 = SHA256({
  "schema_version":"odlrq.e2.matrix-property.v1",
  "endpoint_id":"u24_e2_declared_square_endpoint_v1",
  "basis_convention":"target_row_source_column_v1",
  "target_coordinate_ids":["OPEN_0","OPEN_1"],
  "source_coordinate_ids":["OPEN_0","OPEN_1"],
  "rows":<restricted Mat(2,2)>
})

restricted_{source|target}_weights_sha256 = SHA256({
  "schema_version":"odlrq.e2.weight-vector-property.v1",
  "endpoint_id":"u24_e2_declared_square_endpoint_v1",
  "role":"SOURCE" or "TARGET",
  "coordinate_ids":["OPEN_0","OPEN_1"],
  "values":<the exact two-R array>
})

omitted_cells_sha256 = SHA256({
  "schema_version":"odlrq.e2.omitted-cells-property.v1",
  "endpoint_id":"u24_e2_declared_square_endpoint_v1",
  "basis_convention":"target_row_source_column_v1",
  "full_coordinate_ids":["OPEN_0","OPEN_1","CLOSED","SINK"],
  "rows":<the exact twelve omitted-cell rows>
}).
```

Cocycle and return-memory role-specific weight digests use the identical
weight-vector object with role `SOURCE`, `INTERMEDIATE`, or `TARGET` and their
exact coordinate/value arrays.  These are rederived provenance properties, not
accepted compatibility authorities; compatibility compares IDs and `R` values.

It excludes parent envelope, identification full-wire digest, source law, and
all compressed-coefficient fields.

**`LiftingUniformSafetyCertificate`**, schema
`odlrq.e2.lifting-uniform-safety.v1`, has exactly:

```text
schema_version, endpoint_id, parent_id, source_law_variant, scope,
parent_envelope_sha256, coordinate_identification_sha256,
envelope_restriction_sha256, source_law_sha256,
coordinate_core_sha256, restriction_core_sha256,
ordered_candidate_loads, majorant_matrix, candidate_load_count,
matrix_cell_count, theorem_core_sha256, law_uniform,
cancellation_free, verification_disposition.
```

`ordered_candidate_loads` has exactly twenty rows in target-coordinate,
source-coordinate, then source-frame-member order.  Each row has exactly

```text
target_coordinate_id, source_coordinate_id,
source_member_id, source_member_sha256, load.
```

`majorant_matrix=Mat(4,4)`.  The theorem-core preimage is exactly section 7.
`law_uniform` and `cancellation_free` are exact booleans rederived true, never
caller pass bits.

**`ResolvedMemorySplit`**, schema `odlrq.e2.resolved-memory-split.v1`, has
exactly:

```text
schema_version, endpoint_id, envelope_restriction_sha256,
basis_convention, retained_coordinate_ids, p_coordinate_ids,
q_coordinate_ids, m_pp, m_pq, m_qp, m_qq,
split_exhaustive, split_core_sha256, verification_disposition.
```

The four block matrices are respectively `Mat(1,1)`.  The split-core preimage
has exactly the same fields except `split_exhaustive`, `split_core_sha256`, and
`verification_disposition`, and replaces the schema with
`odlrq.e2.memory-split-core.v1`; `split_exhaustive` is rederived true.

**`CocycleCertificate`**, schema `odlrq.e2.cocycle-certificate.v1`, has
exactly:

```text
schema_version, endpoint_id, channel, channel_derivation,
composition_scope, product_order, factor_restriction_sha256s,
ordered_source_basis, ordered_intermediate_basis, ordered_target_basis,
source_weights, intermediate_weights, target_weights,
source_weights_sha256, intermediate_weights_sha256, target_weights_sha256,
layer_matrices, theta_values, componentwise_lhs_rows,
product_matrix, product_weighted_norm, theta_product,
finite_horizon, inequality_pass, verification_disposition.
```

`channel` is exactly `P1_BRANCHING_ADJUSTED` or `P2_BRANCHING_ADJUSTED` and
selects its sole derivation from section 9.  `composition_scope` is exactly
`declared_abstract_coordinate_composition_v1`; product order is exactly the
section-9 tag.  Basis arrays each equal `J`; each weight array has two `R`,
`layer_matrices` has two `Mat(2,2)`, `theta_values` has two `R`,
`componentwise_lhs_rows` has two arrays of two `R`, and `product_matrix` is
`Mat(2,2)`.  Each cocycle weight digest uses the exact
`odlrq.e2.weight-vector-property.v1` object with role
`SOURCE`, `INTERMEDIATE`, or `TARGET`, coordinate IDs, and complete `R` array.
Both booleans are rederived true.

**`ReturnMemoryBound`**, schema `odlrq.e2.finite-return-memory.v1`, has
exactly:

```text
schema_version, endpoint_id, envelope_restriction_sha256,
resolved_memory_split_sha256, iteration_scope, finite_only, horizon,
m_pp, m_pq, m_qp, m_qq, qq_powers, return_terms, return_sum,
p_source_weights, p_source_weights_sha256,
p_target_weights, p_target_weights_sha256, weighted_norm,
operation_count, direct_zero_memory_positive,
verification_disposition.
```

`iteration_scope` is exactly the stationary-reuse tag in section 8;
`horizon=3`; each block, power, term, and sum is `Mat(1,1)`.
`qq_powers` and `return_terms` each have exactly three rows with exact keys
`{k,matrix}`.  The two weight digests use the section-11.2 weight-vector
property domain.  `operation_count=10` under the sole counting rule: sequential
`Q` powers require two scalar multiplications after the identity, three
`M_PQ * power * M_QP` terms require six scalar multiplications, and summing
three terms requires two scalar additions; copies and rational reduction are
not counted.  Both booleans are rederived true.

**`CandidateUniverseManifest`**, schema
`odlrq.e2.candidate-universe-manifest.v1`, has exactly:

```text
schema_version, endpoint_id, universe_id, sealed_before_threshold,
candidate_rows, candidate_count, canonical_candidate_ids,
pre_gate_complete, manifest_core_sha256, verification_disposition.
```

`universe_id` is `u24_e2_literal_three_candidate_universe_v1`.
`candidate_rows` has exactly three rows in `[c0,c1,c2]` order, each with

```text
candidate_id, candidate_payload_sha256, source_coordinate_ids,
membership_core_sha256, parent_id, parent_envelope_sha256,
coordinate_identification_sha256, envelope_restriction_sha256,
lifting_uniform_safety_sha256, target_coordinate_id,
source_coordinate_id, bound, utility.
```

`source_coordinate_ids` is an exact one-element coordinate array, not a claim
that the raw E1 block has one member.  The membership-core digest hashes
exactly `{endpoint_id,candidate_id,candidate_payload_sha256,parent_id,
source_coordinate_ids,source_coordinate_id,coordinate_core_sha256}`.  The
manifest-core digest hashes exactly the same top-level wire with
`schema_version="odlrq.e2.candidate-universe-core.v1"` while excluding
`manifest_core_sha256` and `verification_disposition`.  No evidence-status or
ABSTAIN row variant exists in v1.

**`CertifiedSupportToken`**, schema `odlrq.e2.certified-support-token.v1`, has
exactly:

```text
schema_version, endpoint_id, candidate_universe_manifest_sha256,
p1_cocycle_sha256, p2_cocycle_sha256, return_memory_bound_sha256,
comparator, threshold, decision_rows, denominator, numerator, coverage,
ungated_ranking, gated_ranking, support_candidate_ids,
rejected_candidate_ids, abstained_candidate_ids,
ranking_changed, invalidation_sha256, verification_disposition.
```

`decision_rows` has exactly three rows with exact keys
`{candidate_id,bound,threshold,decision,reason,authority_bundle_sha256}`.
`decision` is only `ACCEPT` or `REJECT`; reasons are respectively
`BOUND_LE_THRESHOLD` and `BOUND_GT_THRESHOLD`.  The invalidation preimage has
schema `odlrq.e2.support-invalidation.v1` and binds the endpoint, all four
authority SHA fields, comparator, threshold, all decision rows, denominator,
numerator, both rankings, all three ID arrays, and `ranking_changed`.  It
excludes only its own digest and the disposition.

For each decision row, `authority_bundle_sha256` hashes exactly

```text
{
  "schema_version":"odlrq.e2.decision-authority-bundle.v1",
  "candidate_row":<the complete exact manifest candidate row>,
  "p1_cocycle_sha256":<full SHA>,
  "p2_cocycle_sha256":<full SHA>,
  "return_memory_bound_sha256":<full SHA>
}.
```

`threshold`, `bound`, and `coverage` are `R` wires; the fixed coverage is
exactly `R(2/3)`, never a float or a pair with an unstated interpretation.

The eight exact `verification_disposition` literals are respectively

```text
SourceTargetCoordinateIdentification  E2_SOURCE_TARGET_COORDINATES_IDENTIFIED
EnvelopeRestrictionWitness            E2_ENVELOPE_RESTRICTION_REPLAYED
LiftingUniformSafetyCertificate       E2_DECLARED_FINITE_LIFTING_UNIFORM_VERIFIED
ResolvedMemorySplit                    E2_MEMORY_SPLIT_RESOLVED
CocycleCertificate                     E2_FINITE_ABSTRACT_COCYCLE_VERIFIED
ReturnMemoryBound                      E2_FINITE_RETURN_MEMORY_BOUNDED
CandidateUniverseManifest              E2_DECLARED_CANDIDATE_UNIVERSE_SEALED
CertifiedSupportToken                  E2_BINDING_SUPPORT_CERTIFIED.
```

### 11.3 Exact public signatures and retained-authority access

`FiberEnvelope` does not publicly expose its retained E1 authorities.  The
identification builder therefore receives all nine exact typed authorities;
it may not inspect any E1 private attribute.  It calls public `to_dict` on the
layer, generators, weights, law, and completeness witnesses, cross-checks every
digest in `envelope.to_dict`, and replays public `FiberEnvelope.from_dict` with
the same authorities before deriving a coordinate.  Its exact signature is

```python
identify_e2_source_target_coordinates(
    *,
    envelope: FiberEnvelope,
    layer: DeclaredSyntheticTransferLayer,
    source_generator: ExactQuotientCoordinateGenerator,
    target_generator: ExactQuotientCoordinateGenerator,
    source_weights: PositiveFiberWeights,
    target_weights: PositiveFiberWeights,
    source_law: ExactFiniteFiberLaw,
    source_completeness: FiberCompletenessWitness,
    target_completeness: FiberCompletenessWitness,
) -> SourceTargetCoordinateIdentification
```

`parent_id` and `source_law_variant` are not inputs.  The builder privately
reconstructs the section-5.1 canonical fixture authorities through the same
accepted public builders and first requires byte equality of the source/target
generator wires, complete raw member/payload/transition/partition frames,
signed layer wire, both weight wires, both completeness wires, and all member-
set rows.  Only then does it require the exact abstract matrix and assign the
sole matching literal in `[M0,M1,MRET,NONNORMAL,NILPOTENT]`.  The source-law
wire must be the exact `PRIMARY` wire for that parent, except that exact
`ALTERNATE_M0_DIAGNOSTIC` is additionally admitted only for the M0
law-invariance diagnostic.  Zero/multiple fixture matches, another exact law,
or the same majorant arising from different raw data fails.  Thus a caller
label or matrix coincidence cannot become scientific authority.

The resulting sealed identification privately retains those exact objects so
later builders can rederive through public APIs.  The remaining builders are
exactly

```python
build_e2_envelope_restriction(
    *, envelope: FiberEnvelope,
    identification: SourceTargetCoordinateIdentification,
) -> EnvelopeRestrictionWitness

certify_e2_lifting_uniform_safety(
    *, envelope: FiberEnvelope,
    identification: SourceTargetCoordinateIdentification,
    restriction: EnvelopeRestrictionWitness,
) -> LiftingUniformSafetyCertificate

resolve_e2_memory_split(
    *, restriction: EnvelopeRestrictionWitness,
) -> ResolvedMemorySplit

certify_e2_cocycle(
    *, channel: str,
    first: EnvelopeRestrictionWitness,
    second: EnvelopeRestrictionWitness,
) -> CocycleCertificate

bound_e2_finite_return_memory(
    *, restriction: EnvelopeRestrictionWitness,
    split: ResolvedMemorySplit,
) -> ReturnMemoryBound

build_declared_e2_candidate_universe(
    *,
    m0_identification: SourceTargetCoordinateIdentification,
    m0_restriction: EnvelopeRestrictionWitness,
    m0_safety: LiftingUniformSafetyCertificate,
    m1_identification: SourceTargetCoordinateIdentification,
    m1_restriction: EnvelopeRestrictionWitness,
    m1_safety: LiftingUniformSafetyCertificate,
) -> CandidateUniverseManifest

apply_e2_binding_gate(
    *, manifest: CandidateUniverseManifest,
    p1_cocycle: CocycleCertificate,
    p2_cocycle: CocycleCertificate,
    return_memory: ReturnMemoryBound,
) -> CertifiedSupportToken
```

Every builder and parser enforces the fixed role/law table before any output:

```text
restriction/safety diagnostic   the exact identification parent and its own
                                PRIMARY law, or ALT only for M0 diagnostic
cocycle first/second            PRIMARY M0, then PRIMARY M1
memory split/return             PRIMARY MRET
candidate universe              PRIMARY M0 authorities and PRIMARY M1
binding gate                    the P1/P2 cocycles from PRIMARY M0->M1 plus
                                the PRIMARY MRET return bound.
```

`NONNORMAL` and `NILPOTENT` are restriction/norm diagnostics only.  An
alternate-law M0 certificate cannot enter a cocycle, manifest, or support token.

The exact strict parser signatures are

```python
SourceTargetCoordinateIdentification.from_dict(
    value: dict,
    *,
    envelope: FiberEnvelope,
    layer: DeclaredSyntheticTransferLayer,
    source_generator: ExactQuotientCoordinateGenerator,
    target_generator: ExactQuotientCoordinateGenerator,
    source_weights: PositiveFiberWeights,
    target_weights: PositiveFiberWeights,
    source_law: ExactFiniteFiberLaw,
    source_completeness: FiberCompletenessWitness,
    target_completeness: FiberCompletenessWitness,
) -> SourceTargetCoordinateIdentification

EnvelopeRestrictionWitness.from_dict(
    value: dict, *, envelope: FiberEnvelope,
    identification: SourceTargetCoordinateIdentification,
) -> EnvelopeRestrictionWitness

LiftingUniformSafetyCertificate.from_dict(
    value: dict, *, envelope: FiberEnvelope,
    identification: SourceTargetCoordinateIdentification,
    restriction: EnvelopeRestrictionWitness,
) -> LiftingUniformSafetyCertificate

ResolvedMemorySplit.from_dict(
    value: dict, *, restriction: EnvelopeRestrictionWitness,
) -> ResolvedMemorySplit

CocycleCertificate.from_dict(
    value: dict, *, channel: str,
    first: EnvelopeRestrictionWitness,
    second: EnvelopeRestrictionWitness,
) -> CocycleCertificate

ReturnMemoryBound.from_dict(
    value: dict, *, restriction: EnvelopeRestrictionWitness,
    split: ResolvedMemorySplit,
) -> ReturnMemoryBound

CandidateUniverseManifest.from_dict(
    value: dict, *,
    m0_identification: SourceTargetCoordinateIdentification,
    m0_restriction: EnvelopeRestrictionWitness,
    m0_safety: LiftingUniformSafetyCertificate,
    m1_identification: SourceTargetCoordinateIdentification,
    m1_restriction: EnvelopeRestrictionWitness,
    m1_safety: LiftingUniformSafetyCertificate,
) -> CandidateUniverseManifest

CertifiedSupportToken.from_dict(
    value: dict, *, manifest: CandidateUniverseManifest,
    p1_cocycle: CocycleCertificate,
    p2_cocycle: CocycleCertificate,
    return_memory: ReturnMemoryBound,
) -> CertifiedSupportToken
```

No builder accepts a precomputed digest, pass bit, matrix, weight, threshold,
horizon, candidate row, evidence status, or list of support IDs.  The gate is
the sole support-token constructor.  Private retained E1 references are
capabilities for rederivation only and never become a public alternate wire.

## 12. Exact future implementation mapping and additive allowlist

After the final authority commit is pushed and its exact known control-red is
adjudicated under sections 2--3, the user instruction recorded in section 2 is
the implementation license.  The scientific source-freeze commit is a direct
child of accepted E1 and may change exactly these four paths:

```text
lean_rgc/odlrq/certificates.py
lean_rgc/odlrq/selection.py
tests/test_odlrq_selection.py
tests/tier_manifest.json
```

The first three are new files.  The manifest receives only the filename-level
`unit` registration for `tests/test_odlrq_selection.py`.  Runner preflight parses
the parent and semantic-commit manifests as JSON objects and requires the
parent mapping to be byte-semantically preserved, with exactly one new mapping
`"test_odlrq_selection.py": ["unit"]`; no existing key, array order, value, or
other row may change.  All four paths have
Git mode `100644`.  `certificates.py` and the test module each contain exact
literal constants for the final authority commit SHA, authority tree, authority
document path, and document Git blob; import-time and test-time checks require
them to agree.  This content-addressed sibling binding prevents a post-hoc
authority choice without placing the unregistered document row in scientific
ancestry.

Only after that four-path semantic commit exists locally may one runner-control
**carrier merge** be constructed on a separate fixed ref.  Its first parent is
the final authority commit, its second parent is the semantic commit, and its
tree is exactly the authority tree plus one changed path:

```text
tools/run_uprime_e2_endpoint_tests.ps1
```

with mode `100644`.  No semantic source, test, or manifest byte is present in the
carrier-merge tree.  The merge embeds the authority commit/tree/document blob
plus the semantic commit/tree and all four semantic Git blobs.  Its sole purpose
as a two-parent commit is to make the otherwise-unpublished semantic commit
content-addressed and remotely reachable without checking out or CI-executing
its tree.  It is never merged into the accepted branch.

The carrier merge is pushed immutably before the one-shot run.  The phase-local
topology oracle lives in this runner and verifies exact ordered parents
`[authority,semantic]`, the authority and runner-control remote tips, the absent
build/success-closeout/failure-closeout refs, the unchanged accepted ref, the
semantic/E1 four-path diff, the runner/authority one-path diff, modes, clean
runner worktree, immutable E1 blobs, materialized raw bytes, and Git-filtered
blob OIDs before it arms Python.  A complete bounded `ls-remote --heads --tags`
census must contain no direct head, lightweight-tag target, or annotated-tag
peeled target equal to the semantic commit.  The exact sorted census payload,
byte length, and SHA are bound into the pre-run manifest.  This proves only the
advertised current remote-tip state; deleted refs or an unadvertised historical
execution remain outside the claim.  This is fresh E2 source binding, not a
repair or invocation of an R7--R13 guard.

No accepted E1 file, old U2--U4 runner, workflow, guard, identity test, result,
closeout, external wrapper, ledger, cache, publisher, or unrelated path is in
either allowlist.

This document itself is an authority-side one-path commit.  The three new
semantic files and runner path are absent there; the already existing tier
manifest is byte-identical to accepted E1.

## 13. New in-repository E2 runner; external capture bypass

The only future local E2 command is

```powershell
& .\tools\run_uprime_e2_endpoint_tests.ps1
```

It accepts no argument, selector, caller path, wall, cap, environment override,
or test expression.  It selects exactly `tests/test_odlrq_selection.py` and
requires exactly ten passed tests with zero skip, xfail, deselection, or extra
node.  It never runs B0, E0, E1, ME0, S0, I0, the M3 exhaustive suite, or a
historical runner.

This is a new fresh-authority runner, not a modification or rerun of any R7--R13
control state.  It reuses only the simple lane-isolated runner skeleton seen in
the accepted M4--M6 pattern recorded by
amendment `2712060ff5b0223aa581dd611363dba517520048` and closeout
`5bb86a43fbd05731dd7e5db25394995139854805`.  The historical accepted runner
blobs are:

```text
M4 e9a035102e1de10ffeae650b2b75a903383aeb40
M5 c9591c5c8f80daeef1dd79ddc156647280cec68f
M6 1bd9ac83d152154037964a6a49145c6d9eb22b92.
```

Those blobs do not establish the E2 archive/materialization procedure, held-
handle semantics, private runtime, one-shot latch, bounded pumps, or any E2
feasibility claim.  The first official invocation remains fail-closed with zero
correction budget.  Fresh E2 specifies the following independently audited
controls:

```text
monitored wall            180 seconds
qualification threshold   60 seconds
qualification predicate   3 * elapsed_ticks <= wall_ticks
Job process memory cap     2,147,483,648 bytes
Job aggregate memory cap   2,147,483,648 bytes
combined stdout/stderr cap 67,108,864 bytes
active process limit       1
poll interval              25 ms
```

The wall is parent-monitored rather than an OS deadline primitive: expiry is
detected and the owned Job is closed within one 25-ms poll interval plus Windows
scheduler delay.  Process-count and memory containment are Job Object limits;
the wall is not mislabeled OS-hard.

The parent in-repo PowerShell script starts one direct Python process with
`System.Diagnostics.Process`, `UseShellExecute=false`, no shell, and exact
interpreter switches `-I -S -B -X utf8`.  It clears the child environment and
adds only the frozen Windows system/temp values plus
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`; it passes arm, receipt, private source root,
and private runtime root as internal bootstrap arguments, then overwrites both
`sys.argv` and CPython's preserved `sys.orig_argv` with fixed path-free arrays
before test collection.  The child current directory is the owned
private source root, never the mutable checkout.

The local scientific interpreter is exactly Windows x86-64 Python `3.13.7` at
`C:\Python313\python.exe`, SHA-256
`D932E5E2F324D57F392E8FD063DCF6D0185BE8A664C57C6D24E7762ED02C28CA`.
The parent is Windows PowerShell Desktop `5.1.26100.8655`, x64, at
`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`, file version
`10.0.26100.8457`, SHA-256
`0FF6F2C94BC7E2833A5F7E16DE1622E5DBA70396F31C7D5F56381870317E8C46`.
Topology preflight uses only `C:\Program Files\Git\cmd\git.exe`, Git
`2.54.0.windows.1`, executable SHA-256
`81EF35AE005CA9318018D18E3327578CE939FB99FEAAD6B2D7C8AB15F3DE8DB5`.
Local pytest is exactly `9.0.3`; its imported `pytest/__init__.py` SHA-256 is
`7BE7A1E2218DC59A19D1AD131E4ABE21172A295087EFC72898938248782E8766`.
The admitted third-party distribution set is exactly `pytest==9.0.3`,
`pluggy==1.6.0`, `iniconfig==2.3.0`, `packaging==25.0`,
`pygments==2.19.2`, `colorama==0.4.6`, and `numpy==2.3.3`.  NumPy is admitted
only because the tracked `lean_rgc/__init__.py -> carrier.py` import chain loads
it before an ODLRQ submodule; the new E2 modules/tests may not directly import
or call NumPy.  This preserves hosted package-import semantics without editing
the accepted root package.  The future committed runner freezes
their sole source root as
`C:\Users\yusei\AppData\Roaming\Python\Python313\site-packages` and freezes
one literal aggregate manifest SHA over the exact files admitted from those seven
distribution `RECORD`s and verifies every recorded file hash before use.  The
aggregate preimage is canonical sorted rows
`{distribution,version,relative_posix_path,byte_count,sha256}` for every
RECORD-listed file plus each RECORD file itself.  The only admitted escaping
rows are exactly `../Scripts/py.test.exe`, `../Scripts/pytest.exe`,
`../Scripts/pygmentize.exe`, `../Scripts/f2py.exe`, and
`../Scripts/numpy-config.exe`; their bytes are verified and included in the
aggregate from the canonical sibling `Scripts` directory but are not copied or
placed on `PATH`.  Every other escaping row fails.  Directories, `.pyc`,
`__pycache__`, and unlisted site-package files are excluded.  Destination
normalization uses Windows case-insensitive full paths and rejects normalized
collisions, ADS/colon names, reserved device names, reparse points, and root
escape.  Missing RECORD hash for a non-RECORD file or hash mismatch fails.  Any
listed runtime drift stops before the attempt marker is created.  This is a
listed-runtime baseline, not a proof that every Windows or Python standard-
library byte is globally identical.
The new E2 source and tests use the repository exact-rational layer and Python
standard library; they do not directly import NumPy or another numeric package.  Hosted
Python 3.11 CI is separate cross-version integration evidence and makes no
Windows wall, Job-memory, or capture claim.  Canonical wires and exact endpoint
values must agree across the two interpreters.

Before starting Python, the parent verifies `HEAD` is the sole runner-control
carrier merge specified in sections 12 and 15, its ordered parents are exactly
the final authority commit and the four-path semantic source-freeze commit,
that semantic commit is a direct child of accepted E1, and the separately named
authority ref resolves to the exact document/blob constants embedded in both
source and runner.  Its checked-out tree must equal the authority tree plus only
the runner path: the three new semantic files are absent and the existing
`tests/tier_manifest.json` equals its accepted-E1 blob.  The runner path records
two checkout identities: uppercase SHA-256 of local raw bytes, and the Git blob
OID after repository filters (`git hash-object --path`), which must equal the
named runner blob.  Each of the four semantic paths records the corresponding
raw SHA only after materialization from the second-parent tree, paired with that
semantic commit's Git blob.  Raw SHA and Git blob are never equated; checkout
EOL conversion can make them differ.

All pre-marker Git calls are themselves bounded control-plane processes: at
most 32 invocations, a 15-second wall for each local call, a 30-second wall for
each `ls-remote`, a 120-second aggregate Git wall, and 1,048,576 combined output
bytes per call.  Each is started without a shell, with
`GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=Never`, cleared askpass variables, and
`-c credential.interactive=never`; stdout/stderr use the same bounded-reservation
pattern at the smaller cap.  A fixed in-script `CreateProcessW` launcher starts
each Git process with `CREATE_SUSPENDED`, assigns it to a fresh transient
`KILL_ON_JOB_CLOSE` control Job, and only then calls `ResumeThread`; failed
creation/assignment/resume terminates the suspended process and blocks.  On
timeout the parent closes that Job.  The control pumps then have a separate
two-second EOF deadline; missing EOF causes their local read handles to be
disposed, records `control_pipe_escape=true`, and returns
`U24_E2_RUNNER_BLOCKED` without an unbounded wait.  Assignment/cleanup failure
also blocks.
These checks occur before durable attempt-marker creation and make no scientific
pass claim.

To close the checkout hash/import race, the parent uses the frozen Git
executable with `archive --format=zip --output=<owned-new-zip>` and the exact
semantic commit plus pathspecs `lean_rgc/` and
`tests/test_odlrq_selection.py` and `tests/tier_manifest.json`.  It opens that ZIP with
`System.IO.Compression.ZipArchive` from PowerShell 5.1, validates the complete
entry set, normalized non-ADS/non-device relative paths, modes, sizes, and no
duplicate/case-fold collision before extracting any entry, then extracts into
a fresh canonical non-reparse directory.  No `tar`, shell pipeline, or mutable
checkout copy is used.  It copies only the seven
verified runtime distributions into a separate private runtime directory.  It
rehashes the materialized E2 files against the committed blobs, opens every
materialized source/runtime file read-only with sharing that permits reads but
denies write/delete, and retains all handles until the Job closes.  Python is
given only the materialized repository root, private runtime root, and its
isolated standard-library paths; it never imports an E2 or accepted-E1 module
from the mutable checkout.  The parent script itself is the already parsed
committed runner and verifies its raw checkout SHA/blob before materialization;
defence against a malicious replacement before PowerShell parses that script
is outside this host-local runner claim.

The canonical pre-run manifest binds the authority commit/tree/document blob,
semantic source commit/tree/direct E1 parent/four-path diff, runner commit/tree/
ordered two parents/authority-relative one-path diff, the authority and runner-
control remote refs, absent build/success/failure refs, unchanged accepted-E1
ref, complete sorted heads/tags census payload/length/SHA and no-semantic-tip
check, checkout raw SHA/blob pairs, materialized raw
SHA/blob pairs, immutable E1 blob OIDs, clean-status proof, private-tree archive
SHA, listed-runtime aggregate SHA, and all listed runtime identities.  Before
child creation the parent emits the **complete** canonical manifest payload,
then its byte length and SHA-256 outside the payload.  Every terminal closeout
copies all three, not merely the digest.

The one-shot key is the exact tuple `(authority commit, semantic commit,
runner-control commit)`.  Immediately before child
creation the parent validates each component of the canonical LocalAppData
parent path as non-reparse, then exclusively creates, with .NET
`FileMode.CreateNew`, the single persistent **host/account-local** latch

```text
%LOCALAPPDATA%\lean-rgc-automation\uprime-e2-attempts\<authority>-<semantic>-<runner>\attempt-consumed.json
```

Its minimal canonical JSON binds schema, endpoint, authority commit/tree,
semantic commit/tree, runner commit/tree, pre-run-manifest SHA,
`attempt_consumed_before_child=true`, and UTC
creation time.  The parent writes through a `FileStream`, calls durable
`Flush(true)`, closes, reopens, rehashes, and only then creates Python.  A
pre-existing latch blocks before Python creation.  The latch is never deleted
or rewritten, including on bootstrap, timeout, crash, or failure.  Its exact
bytes and SHA-256 are copied into the terminal closeout.  It is the sole bounded
one-shot latch expressly allowed by section 18, not a multi-entry evidence
registry or retry publisher.  It does **not** prevent an administrator from
deleting/tampering with it or the same authority from running on another host
or account; global/tamper-proof one-shot enforcement is not claimed.

Before waiting, the bootstrap asserts `sys.flags.isolated == 1`,
`sys.flags.no_site == 1`, bytecode disabled, no user site, no imported
`sitecustomize`/`usercustomize`, and an exact isolated pre-arm `sys.path` that
contains neither checkout, private repository, nor third-party path.  It then
performs only a standard-library wait for the exact arm file and does not
import pytest or a scientific module before arm.  The parent assigns the
process to a Windows Job Object with `ACTIVE_PROCESS_LIMIT=1`, per-process and aggregate
2-GiB memory limits, and `KILL_ON_JOB_CLOSE`; only after successful assignment
does it exclusively and atomically create an arm file containing exact ASCII
bytes `ARM\n`.  This closes the start-to-assignment race before scientific
imports.  A pre-existing arm path, wrong bytes, failed exclusive create, or
child scientific import before arm is a hard runner failure.

After arm and before adding either private path, the bootstrap imports the
standard-library `subprocess`, `socket`, `os`, `asyncio`, and `multiprocessing`
control modules, replaces their process-creation/network entry points with the
exact denial callable, and installs an audit hook rejecting actual
`subprocess.Popen`, socket connect/bind/listen, `os.system`, and spawn/exec
events.  Importing these standard-library modules remains allowed because
pytest imports `subprocess` at module load; creating a process or network
connection does not.  It then adds only the held private source/runtime roots,
AST-parses the two E2 source files and test module from that materialization,
and rejects **direct E2** imports whose root is in the exact set
`{aiohttp,asyncio,builtins,cffi,ctypes,ftplib,glob,http,importlib,io,
multiprocessing,os,pathlib,requests,shutil,socket,ssl,subprocess,sys,tempfile,
urllib}` plus direct calls named `open`, `eval`, `exec`, `compile`, or
`__import__`.  There is no general native-loader prohibition: the manifest-
verified NumPy `.pyd`/DLL files may be loaded by the frozen dependency chain,
while the E2 source and test AST may not directly import or call NumPy,
`ctypes`, `cffi`, or `importlib`.  The runtime audit hook enforces the separately
enumerated process/network events; it is not described as a universal dynamic-
code hook.  When the accepted `lean_rgc` root later imports `subprocess`, Python
returns the already loaded and patched standard-library module from
`sys.modules`; package import therefore does not bypass or conflict with the
denial order.
Only after those denials and the AST audit does it import the privately
materialized pytest/NumPy chain and collect E2.  The fixed tests use only in-memory fixture
values; no protected-path literal or input is passed to the child.  The Job
Object is the hard process-count boundary.  Before pytest import, the bootstrap
itself performs one fixed `subprocess.Popen` probe and one fixed loopback socket-
connect probe through the patched entry points; both must raise the exact denial
exception before an OS action and are recorded in the child receipt.  The E2
test source therefore does not need a forbidden direct process/network import.

This Windows runner is **not** an OS filesystem or network sandbox.  The
protected-read claim is therefore limited to the exact static I/O-free source
contract, fixed in-memory fixtures, no protected-path literal/input, private
materialization, and audited common API denial.  The unsandboxed child still
has ambient Windows filesystem/network capability.  A later-discovered alternate filesystem or network
escape invalidates E2 and stops; this document does not falsely claim kernel
prevention.  The private child-receipt path is removed from the child environment,
`sys.argv`, and `sys.orig_argv`; the bootstrap verifies all three before
collection and records
`receipt_path_hidden=true`.  E2 test code is not given the path.

The parent runs two fixed 16,384-byte bounded pumps over the redirected raw-byte
pipes.  They reserve each chunk with an `Interlocked.CompareExchange` retry loop
against one shared counter; a reservation that would take retained combined
output above `67,108,864` is rejected, not appended, and causes immediate owned-
Job termination.  The report keeps separate stdout/stderr retained and dropped
byte counts.  Stream scheduling can change which final chunk is retained on an
output-cap failure, so cap-failure capture bytes are explicitly not a
deterministic scientific artifact.  No unbounded `CopyToAsync` or `ReadToEnd`
is used.  On normal
exit or cap failure the parent waits for or terminates the owned Job, waits for
both pumps to reach EOF, flushes and disposes the capture write streams, and
only then reads retained capture bytes.  It never reads a capture file while a
write-side stream is open.  With active process limit one, no successful
descendant can retain stderr; consequently the R13 descendant-stderr hypothesis
remains **unadjudicated and bypassed**, not repaired or declared false.

The bootstrap exclusively creates a canonical ASCII **child receipt** before it
exits.  Its payload contains only facts available inside that process:

```text
schema_version, lane, authority_commit, authority_tree,
authority_document_blob, source_commit, source_tree,
runner_commit, runner_tree,
pre_run_manifest_sha256, attempt_marker_sha256,
expected_node_ids, collected_node_ids, node_reports,
passed_node_ids, failed_node_ids,
skipped_node_ids, xfailed_node_ids, deselected_count, tests_passed,
receipt_path_hidden, spawn_denial_probe_pass, network_denial_probe_pass,
pytest_exit_code,
test_module_materialized_sha256, test_module_git_blob,
certificates_materialized_sha256, certificates_git_blob,
selection_materialized_sha256, selection_git_blob,
disposition.
```

The node arrays contain full fixed pytest node IDs in collection order;
`node_reports` contains exact rows `{node_id,when,outcome,was_xfail}` for every setup,
call, and teardown report in arrival order, where `when` is one of
`setup,call,teardown`, `outcome` one of `passed,failed,skipped`, and `was_xfail`
is a strict boolean derived from the pytest report.  The summary arrays are
deterministically derived from those rows.  A node is passed iff it has a call
report and setup, call, and teardown all pass; a missing call report is never
classified passed, and any setup/call/teardown failure classifies the node
failed.  A
fixed programmatic pytest plugin inside the frozen bootstrap records collection
and terminal reports directly; no capped stdout/stderr text is parsed for node
identity or outcome.  Duplicate, reordered, unreported, or extra nodes fail the
child receipt.

Only after the native child has exited or been terminated, the Job has reported
its final state, both pumps have reached EOF, capture writers are closed, and
cleanup is adjudicated does the parent exclusively create a separate canonical
ASCII **outer execution report**.  It contains

```text
schema_version, lane, authority_commit, authority_tree,
authority_document_blob, source_commit, source_tree,
runner_commit, runner_tree,
pre_run_manifest_sha256, attempt_marker_sha256,
child_receipt_status, child_receipt_payload, child_receipt_parse_error,
child_receipt_byte_length, child_receipt_sha256,
native_process_exit, child_pytest_exit,
elapsed_ticks, clock_frequency, peak_job_memory_bytes,
stdout_retained_bytes, stderr_retained_bytes,
stdout_dropped_bytes, stderr_dropped_bytes,
wall_expired, memory_limit_observed, output_limit_observed,
test_module_materialized_sha256, test_module_git_blob,
runner_checkout_raw_sha256, runner_git_blob,
certificates_materialized_sha256, certificates_git_blob,
selection_materialized_sha256, selection_git_blob,
tier_manifest_materialized_sha256, tier_manifest_git_blob,
cleanup_complete, disposition.
```

`child_receipt_status` is exactly `ABSENT`, `INVALID`, or `VALID`.  For `VALID`,
`child_receipt_payload` is the complete parsed canonical child object, its byte
length/SHA are independently recomputed, `child_receipt_parse_error=null`, every
duplicated identity/source digest must match, and native process exit must equal
`child_pytest_exit`.  For `INVALID`, payload and `child_pytest_exit` are null,
but the bounded raw file's exact byte length and SHA are retained and
`child_receipt_parse_error` is one of `NON_ASCII`, `TRUNCATED`,
`NONCANONICAL`, `WRONG_SCHEMA`, `WRONG_KEYS`, or `IDENTITY_MISMATCH`.  For
`ABSENT`, payload/length/SHA/child exit are null and parse error is
`FILE_ABSENT`.  The child writer and parent reader both enforce a 1,048,576-byte
receipt cap before parsing; an over-cap file is `INVALID` with exact file length,
null SHA, and `SIZE_CAP_EXCEEDED`.  No node outcome is invented for `INVALID` or
`ABSENT`.  The parent
prints the complete canonical outer report plus its exact byte length and SHA-
256 outside the hashed payload, so a closeout reviewer can reconstruct both
layers independently.  Parent-only Job, wall, pipe, and cleanup telemetry never
appears in the child receipt.  Together with the complete pre-run manifest, the
five SHA/Git-blob pairs identify the exact checkout or held materialized bytes,
as named, and the exact committed bytes that were qualified.  The
semantic commit must contain exactly the four semantic blobs, while the runner
commit contains exactly the fifth runner blob; neither may have a sixth changed
path and no later semantic/runner commit is created from a passing result.

It fails independently on argument use, path/reparse escape, missing test,
Python/runtime drift, timeout `124`, margin `125`, memory `137`, output `138`,
nonzero pytest, wrong collection/count, missing or malformed child receipt or
outer report, exit
disagreement, bounded-pump failure, or cleanup escape.  Exit `137` is used only
when a Job completion/violation record positively identifies the memory limit.
A child `MemoryError` or other nonzero exit without that record remains a
generic child failure; hard containment is claimed, not perfect causal
classification.  Both bootstrap denial probes must be true; no separate
process-count telemetry disposition is invented without a completion-port
event.
No success artifact or partial scientific claim is emitted on failure.

Failure classification is mechanical:

```text
wrong parent/diff/mode/blob/clean tree/E1 blob  U24_E2_SOURCE_FREEZE_BLOCKED
runtime/site/path/materialization/AST/arm/marker/receipt/pipe/cleanup control
                                                U24_E2_RUNNER_BLOCKED
exit 124, 125, positively observed 137, 138, or unclassified MemoryError
                                                U24_E2_RESOURCE_OR_SCOPE_BLOCKED
collection/count failure or multiple/unexpected failed test nodes
                                                U24_E2_RUNNER_BLOCKED
test nodes 1, 6, 8, or 10 alone              U24_E2_TYPE_OR_WIRE_BLOCKED
test nodes 2, 3, 4, or 5 alone               U24_E2_ENVELOPE_BLOCKED
test node 7 alone                            U24_E2_RESOURCE_OR_SCOPE_BLOCKED
test node 9 alone                            U24_E2_GATE_NONBINDING.
```

Hosted build/accepted CI uses the same exact-node mapping for this module;
failure elsewhere is recorded as CI/integration failure under
`U24_E2_RUNNER_BLOCKED`, without relabeling an unobserved scientific endpoint.

## 14. Exact ten-test endpoint

`tests/test_odlrq_selection.py` contains exactly these ten undecorated,
unparameterized, top-level tests in order:

```text
test_e2_square_parent_coordinate_identification_rederives_complete_typed_basis
test_e2_restriction_replays_full_parent_terminal_zeros_and_restricted_weights
test_e2_lifting_uniform_safety_is_law_independent_and_cancellation_free
test_e2_p1_p2_cocycles_match_products_weighted_norms_and_limited_derivations
test_e2_return_memory_split_stationary_semantics_and_finite_sum_are_exact
test_e2_orientation_basis_weight_split_and_transport_mutations_fail_closed
test_e2_caps_horizon_work_and_preallocation_bombs_fail_before_authority
test_e2_fixed_candidate_universe_prevents_prefilter_omission_and_accepts_boundary
test_e2_gate_is_coverage_complete_nonempty_reachable_and_top_ranking_binding
test_e2_strict_roundtrip_invalidation_tier_firewall_and_nominal_fallback
```

No parameterization, generated tests, aliases, collection hooks, marks,
`__test__`, `pytestmark`, wrappers, rebinding, or hidden node is permitted.

Independent positive rederivation covers all five `4 x 4` parents, all twelve
terminal zeros per parent, both restricted weights, P1 `15/2 <= 35/4`, P2
`149/4 <= 629/16`, `R_3=21/2`, the three-row manifest, support `[c0,c2]`,
coverage `2/3`, and top-ID change `c1 -> c2`.
The primary/alternate M0-law diagnostic simultaneously requires different
parent, full-identification, full-restriction, and full-safety SHA values, equal
coordinate/restriction/theorem core SHA values, and byte-identical candidate-
load proofs.

Mandatory kills include raw `2 x 2` admission, source/target swap,
non-bijection, missing/nonzero terminal cell, retained reorder, stale
parent/weight/completeness, P/Q gap/overlap/empty/reorder, transpose, `M0 M1`
reversal, intermediate basis/weight mismatch, missing stationary-iteration
tag, unequal stationary source/target weight, P1/P2 or derivation substitution,
nonpositive/float weight, signed-compressed safety substitution, source-law
specific theorem core, generic/prefiltered/missing/duplicate/reordered candidate
rows, unrelated membership, strict `<`, denominator `2`, dropped reject or
hand-written `ABSTAIN`, nullable/empty token, stale digest, permissive parse,
and preallocation bomb.

The future local E2 runner endpoint is exactly `10 passed, 0 skipped, 0
xfailed, 0 deselected`.  On an otherwise unchanged accepted-E1 repository, the
future hosted full-suite endpoint is expected to be exactly

```text
2610 passed, 8 skipped, 161 deselected.
```

Those counts are preregistered expectations, not observations made by this
authoring draft.

## 15. Future execution and CI order

The user instruction recorded in section 2 licenses continuation after this
authority is frozen.  The exact order is:

1. Create the authority document commit as a child of accepted E1 (or its sole
   pre-push document correction), push only the authority side ref, and inspect
   full-history CI.  It must show exactly the preregistered single topology
   failure and `2599 passed, 8 skipped, 161 deselected`; any other failure or
   any E2 execution stops.
2. From accepted E1 itself, not from the authority ref, create exactly the four
   semantic paths in section 12.  Embed and independently verify the final
   authority commit/tree/document blob; touch no E1/control byte.
3. Complete static review and independent golden derivation, then create the
   exact four-path mode-`100644` semantic commit.  Its parent is exactly
   accepted E1.  The worktree/index become clean.  This is the sole semantic
   commit whether the later attempt passes or fails.
4. From the final authority tree add only the dedicated mode-`100644` runner,
   with all authority/semantic identities hardcoded, then create the exact
   two-parent carrier merge `[authority,semantic]` specified in section 12.
   Push only its fixed runner-control ref.  The semantic commit becomes remote-
   reachable as second-parent evidence but receives no branch ref.
5. Runner-control CI checks out a tree with no E2 source/test and therefore
   cannot execute the endpoint.  It must show only the known topology node red
   and exactly `2599 passed, 8 skipped, 161 deselected`; any E2 node collection
   or any additional failure stops.  The observation is operator-side and not
   self-embedded by the already immutable runner.
6. Run the argumentless Windows runner once, cold, from the exact clean carrier-
   merge worktree.  It verifies both parents, refs, blobs, and the private
   materialization of the second-parent semantic tree before arming; then it
   must satisfy the exact ten-node endpoint and 3x predicate.  This is the first
   scientific execution of those E2 nodes.
7. Only a passing one-shot licenses creating/pushing the fixed build ref at the
   already tested semantic SHA.  No post-pass source or runner amend is
   permitted.  Failure leaves the semantic commit reachable through the runner
   merge and creates an append-only failure closeout from that runner merge.
8. Require green full-history hosted CI on the build ref at exactly
   `2610 passed, 8 skipped, 161 deselected`.
9. Only that green semantic SHA may fast-forward byte-identically, without
   merge or content change, from accepted E1 to `codex/uprime-odlrq-plan` and
   receive a distinct green accepted CI with the same count.
10. Record one concise success/failure closeout as a document-only child of the
    runner carrier merge.  Its checked-out tree still contains no E2 source/test;
    CI must show only the known topology-control red with `2599` other passes.
    Closeout CI is observation, not an acceptance gate, and is recorded in the
    single section-3 create-new terminal-observation file.  Do not start ME0 in
    the same phase.

No local warmup, calibration run, direct pytest, source-changing retry,
same-SHA Actions rerun, alternate runner, or endpoint-equivalent invocation
substitutes for the one registered cold run.

The fixed refs and subjects are

```text
authority ref      codex/uprime-e2-endpoint-authority-a0
initial authority subject
                   uprime: freeze fresh E2 endpoint semantics
corrected authority subject (only if the one pre-push correction is used)
                   uprime: correct fresh E2 endpoint authority
build ref          codex/uprime-e2-endpoint-build
build subject      uprime: qualify exact E2 endpoint
runner control ref codex/uprime-e2-endpoint-runner-control
runner subject     uprime: freeze exact E2 endpoint runner
success closeout   codex/uprime-e2-endpoint-closeout
success subject    uprime: close exact E2 endpoint
failure closeout   codex/uprime-e2-endpoint-failure-closeout
failure subject    uprime: close failed E2 endpoint
accepted ref       codex/uprime-odlrq-plan.
```

Each fresh remote publication ref that is actually created is pushed at most
once at its final local tip and is never force-pushed, deleted, repointed, or
reused.  Authority is created first; build/runner exist only if their earlier
gates are reached; exactly one of success/failure closeout may exist, and some
pre-source authority failures intentionally create neither terminal ref.  Normal
movement of an unpublished local branch while creating its licensed commit is
not a remote repoint.
The accepted ref already exists at the selected accepted-E1 predecessor; its
sole licensed movement is one non-force fast-forward from that exact predecessor
directly to the byte-identical semantic SHA after green build
CI.  Accepted-CI red leaves it advanced but does not assign the ACCEPTED
disposition; it is never rewound.
The terminal document path is exactly
`docs/experiments/uprime_odlrq_e2_endpoint_closeout_2026-07-16.md` on success
and
`docs/experiments/uprime_odlrq_e2_endpoint_failure_closeout_2026-07-16.md` on
failure; exactly one of those paths may be created.

## 16. Commit budgets, independent disposition, and stop rules

The document-authoring budget is

```text
MAX_AUTHORITY_INITIAL_COMMITS = 1
MAX_AUTHORITY_DOCUMENT_ONLY_CORRECTIONS = 1
MAX_AUTHORITY_TOTAL_COMMITS = 2
AUTHORITY_PATH_COUNT = 1
```

The optional correction is an immediate single-parent child changing only
this document, with exact subject
`uprime: correct fresh E2 endpoint authority`, and only before the authority
ref is first pushed or any CI is requested.  Only the final corrected tip is
pushed once to the authority ref and receives CI; the initial local commit is
retained in its ancestry but is never independently published or adjudicated.
It cannot repair an inherited
identity/guard/runner/workflow failure, add a path, or weaken an endpoint.  The
initial commit is the direct child of E1; if the correction is used, the final
authority tip is its document-only child and the semantic sibling binds that
final tip.  If authority CI differs from the exact known single-control-red
state, stop at `U24_E2_AUTHORITY_CI_BLOCKED`.

The initial authority commit is the sole planned commit.  The correction is
not additive progress: if a document defect is found before any E2 path exists,
one immediate document-only child may supersede it, and that child becomes the
sole final authority.  It does not permit two corrections or two competing
authorities.

The later E2 budget, if separately licensed, is

```text
MAX_E2_SEMANTIC_COMMITS = 1
MAX_E2_RUNNER_CONTROL_COMMITS = 1
MAX_E2_POST_EXECUTION_CORRECTIONS = 0
MAX_E2_TERMINAL_DOCUMENT_COMMITS = 1.
```

The first official runner attempt is consumed whether it passes or fails.
A failed E2 blocks E2 and every downstream dependent stage but does not alter,
relabel, or invalidate accepted E1.  No scalar aggregate upper-stack status is
used.  Closed dispositions are

```text
U24_E2_ENDPOINT_AUTHORITY_FROZEN_CONTROL_RED
U24_E2_ENDPOINT_SOURCE_FROZEN
U24_E2_ENDPOINT_RUNNER_CONTROL_FROZEN
U24_E2_ENDPOINT_LOCAL_QUALIFIED
U24_E2_ENDPOINT_ACCEPTED
U24_E2_AUTHORITY_AMBIGUOUS
U24_E2_AUTHORITY_CI_BLOCKED
U24_E2_ACCEPTED_E1_DEPENDENCY_BLOCKED
U24_E2_SOURCE_FREEZE_BLOCKED
U24_E2_UNEXPECTED_HOSTED_EXPOSURE
U24_E2_RUNNER_BLOCKED
U24_E2_TYPE_OR_WIRE_BLOCKED
U24_E2_ENVELOPE_BLOCKED
U24_E2_GATE_NONBINDING
U24_E2_RESOURCE_OR_SCOPE_BLOCKED
U24_E2_CLOSEOUT_CI_OBSERVED
U24_E2_CLOSEOUT_CI_OBSERVATION_MISMATCH.
```

`U24_E2_ENDPOINT_AUTHORITY_FROZEN_CONTROL_RED` is assigned only after the final
authority SHA/tree/document blob and the exact preregistered sole-control-red
run/job are observed.  `U24_E2_ENDPOINT_RUNNER_CONTROL_FROZEN` likewise
requires the immutable runner side ref and an operator observation of its exact
sole-control-red with `2599` other tests passing and zero E2 node collected.
Neither is a scientific pass.  The runner embeds and checks the already-
observable authority CI identity plus all Git identities; it cannot embed its
own future Actions run/job identity.  Runner-side CI is therefore checked
outside the one-shot and bound by the terminal closeout.  Local qualification
and accepted scientific CI remain distinct.

Failure topology is append-only and exact:

- unexpected authority-side CI leaves the immutable authority ref/run as the
  terminal evidence and creates no E2 path or attempt; the bridge status
  records `U24_E2_AUTHORITY_CI_BLOCKED` and no repository closeout is fabricated;
- static review or source-freeze creation failure before a semantic commit
  creates the failure-closeout ref from the final authority side tip and records
  zero attempts and no marker;
- runner construction failure after the semantic commit exists creates a two-
  parent failure carrier `[authority,semantic]` whose tree is authority plus
  only the failure document; it records zero attempts, anchors the semantic
  source as second-parent evidence, and contains no E2 files in its checkout;
- runner-control publication or side-CI mismatch without E2 collection creates
  the failure-closeout as a child of the runner carrier merge, records
  `windows_attempt_count=0`, and binds the available authority/source/runner
  identities;
- any E2 node collection in runner-control CI creates the same control-side
  failure closeout but records the exact run/job/log, every recoverable collected
  node ID/outcome, `windows_attempt_count=0`,
  `unexpected_hosted_e2_exposure_count=1`, and disposition
  `U24_E2_UNEXPECTED_HOSTED_EXPOSURE`; it permanently prohibits the Windows
  one-shot and build publication and makes no zero-scientific-exposure claim;
- post-commit pre-marker topology, materialization, runtime, or path preflight
  failure creates the failure-closeout as a one-document child of the runner
  carrier merge and records zero attempts, the complete outer diagnostic and pre-run
  manifest if one was completed, and exact `marker_present=false`;
- a pre-existing marker blocks without a new child; closeout copies and hashes
  the existing marker and records that no new attempt began;
- failure after durable marker creation but before a valid child receipt copies
  the marker, complete available outer diagnostics/capture, source commit and
  five Git blobs, and records the actual `child_receipt_status=ABSENT` or
  `INVALID`; for `ABSENT` it invents no payload/length, and for `INVALID` it
  preserves the bounded raw evidence/error exactly as specified in section 13;
- runner/scientific failure with a valid child receipt copies the marker,
  complete canonical pre-run manifest, child receipt and outer execution report,
  both payloads/lengths/digests, exit mapping, and tested five Git blobs;
- build-CI red creates the failure-closeout as a one-document child of the
  runner carrier merge and records run/job/log classification; the
  accepted ref does not move;
- accepted-CI red creates the failure-closeout as a one-document child of the
  runner carrier merge, binds the identical semantic commit already fast-
  forwarded to the accepted ref, and
  records that acceptance is not adjudicated green; the accepted ref is never
  rewound.

The success closeout is likewise a one-document child of the runner carrier
merge and binds the accepted semantic commit.  Neither closeout ref is an
implementation retry, and neither closeout
commit may change a source, test, runner, manifest, workflow, or accepted E1
byte.

Stop immediately on anchor drift; E1 byte drift; a raw or stale authority;
incomplete restriction or candidate universe; missing restricted weight;
nonexhaustive split; orientation/product/transport mismatch; P2 overclaim;
finite/infinite scope crossing; attempted ABSTAIN/nullable token; nonbinding fixed gate;
cap checked after allocation; unregistered path/process/network; wrong carrier-
merge parent/tree; a second execution, semantic commit, runner-control commit,
or terminal-document commit; an authority correction after first push or CI;
fresh-ref reuse, repoint, deletion, or force-push; any authority/runner/closeout
 CI result outside the section-3 conditional table; protected data read; any
 pre-existing/second terminal-observation record; or any MaxEnt, similarity,
 learner, GPU, SSH, or LLM action.

## 17. Capability boundary and mandatory nonclaims

This authoring phase uses repository reading, a document-only commit, Git push,
and read-only hosted-CI inspection only.  It uses no E2 import or test, no
protected K1--K4 result, reserved task, native Lean/Lake/RPC, SSH, remote CPU,
GPU/CUDA, model server, LLM proposer, weights, knowledge distillation,
deployment, or publication.

A later successful E2 result would establish only the fixed declared finite
synthetic parents, exact restrictions and weights, two finite cocycles, the
finite stationary abstract return-memory bracket, literal three-candidate
universe, and binding gate.  It would not establish:

- a production or all-germ envelope;
- raw-domain iteration, a `FrameMorphism`, compiler transport, or naturality;
- infinite-horizon decay, a resolvent, spectral radius, or uniform-in-time
  stability;
- general second-moment closure from entrywise squares;
- completeness of candidates beyond `[c0,c1,c2]`;
- off-sample locality or witness completeness;
- MaxEnt safety, global-similarity convergence, learner improvement, solve-rate
  benefit, noninferiority, deployment, GPU benefit, or LLM benefit.

MaxEnt remains downstream model selection inside fixed certified support.
Predictive similarity remains distinct from positive-safety similarity.  A
learner may propose future locality coordinates but cannot invent an exact
transition, authority, majorant, or hard bound.

## 18. Anti-fractal clause

This document is the complete answer to the four R6 endpoint questions.  It
does not license another restriction framework, quotient implementation,
candidate registry, evidence ledger, CAS, publisher, recovery coordinator,
external supervisor, wrapper family, alternate runner, per-test amendment, or
control-repair epoch.  Future implementation is exactly two source modules,
one test module, one manifest edit, and one dedicated runner under section 12.
The sole bounded exceptions are section 13's single immutable host-local
`attempt-consumed.json` latch, whose only purpose is to fail a repeated local
invocation for this authority, and section 3's one create-new terminal-CI bridge
record needed because a closeout cannot bind its own future run.  Neither has an
append/update/query/recovery API or may grow into a ledger; their host-local and
tamperable limits are mandatory nonclaims.

The uncommitted R7 amendment and R8 restatement are design precedent only, not
accepted E2 authority and not incorporated by hash or citation as proof.  The
definitions above stand on the accepted E1 types, the construction-bundle
finite formulas, and their own exact frozen endpoint.
