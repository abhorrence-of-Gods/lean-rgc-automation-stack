# U-prime / ODLRQ U'1.5-L0 synthetic locality CEGAR phase-bundle amendment

Date: 2026-07-17 (Asia/Tokyo)

Status: **FROZEN WHEN THIS TWO-FILE AUTHORITY COMMIT IS COMMITTED AND
PUSHED ON THE REGISTERED AUTHORITY REF.**

This amendment turns the already-reviewed locality-learning part of the
upper-stack program into a bounded implementation phase.  It licenses only a
public-synthetic, nominal-only locality CEGAR experiment after accepted I0.
It is an implementation authority, not a second review of the mathematical
program adjudicated on 2026-07-10.

The companion frozen input is:

```text
docs/experiments/inputs/uprime_u15_l0_matrix.json
```

The authority commit contains exactly this document and that input.  The JSON
fixes the action and query catalogues, eight task families, one train instance
and two held-out instances in every family, exact synthetic response tables,
initial partitions, family labels, budgets, and expected seeded witnesses.
Code written after the freeze may validate or consume those bytes; it may not
replace their scientific contents.

### A2 correction record (2026-07-17, Asia/Tokyo)

The immutable primary-A commit
`3155da6ad99105d2ba0ba10124d7372508020a94` was rejected before Phase-B
source work by the final pre-freeze implementation audit.  Its CI run
`29577706277` / job `87875878017` had exactly the predeclared authority shape
`1 failed, 2637 passed, 8 skipped, 161 deselected`; the sole failure was the
old terminal-topology budget guard.  The rejection was not a scientific or CI
failure.  The audit found two endpoint ambiguities: an available seeded pair
could remain co-blocked at `t = 16` without an operative disposition, and a
pre-`P_0` abstention had no exact last-defined loss for the fixed denominator.
This registered A2 replacement makes seed incompleteness `DEGRADED` and makes
failure to seal all 16 exact `P_0` rows `PREREQUISITE_BLOCKED`.  It also fixes
the order so held-out carriers open only after the global train-schedule digest
barrier.  No response table, feature, action, query, family, endpoint value, or
evidence tier changed.

## 1. Scientific base and non-reopening rule

The sole semantic base is accepted I0:

```text
commit  f1df8dd5d92706d907091e6add463fb6c9ca7130
tree    c15e50c683263b50c8ddf371938785d03353b1fc
parent  2376aca8209c38a3a94dfa872334073d86dc4909
subject uprime: implement typed I0 upper-stack candidate
ref     codex/uprime-odlrq-plan
```

Its candidate CI `29569429286` / job `87849472845` and accepted CI
`29569953649` / job `87851123891` were green with exactly
`2638 passed, 8 skipped, 161 deselected`.  I0's seven semantic artifacts were
then emitted, strictly verified, and preserved on the immutable closeout
sidecar:

```text
closeout commit     ee7a1c01dba376881d20962de664f4908acc7b0d
closeout tree       ebc93e941df405b50f425f8c844de2597eaca1f4
closeout parent     f1df8dd5d92706d907091e6add463fb6c9ca7130
closeout ref        codex/uprime-post-e2-upper-stack-closeout
correction commit   c1f1957a3372f80f71b85151a793a4fa0fb218fa
correction tree     e17ced0dbf26b3dd13a0cf6c6f4ba419438dff1f
correction parent   ee7a1c01dba376881d20962de664f4908acc7b0d
correction ref      codex/uprime-post-e2-upper-stack-closeout-correction
```

Those sidecars are bound by commit, tree, parent, and ref but are not merged
into the L0 line.  The accepted hard line remains at `f1df8dd`; L0 cannot move
it or change E0, E1, E2, ME0, S0, I0, their artifacts, or their tier claims.

The 2026-07-10 47-agent verdict remains authoritative: the theory freeze as
then written was rejected, the surviving mathematical core was not refuted,
and the fatal defects were implementation, governance, and endpoint design.
This phase tests whether a finite locality heuristic is useful on a declared
synthetic universe.  It does not rerun that theory review and cannot promote a
synthetic success to production Lean evidence.

### 2026-07-17 red-CI clarifications

The immutable U'0.5 result commit
`cc91a4181a9f87ec10f11727ed787eb7149f955a` has red CI run
`29166670576` / job `86580832840`.  The dated audit found a guard
shallow-history design omission, not a failed scientific probe.  Its exact
candidate commit `3bb3408afc50a08307cff2c9b1906a299739dfb5` passed green CI
run `29166073728` / job `86579287017`.  Future readers must not interpret the
red result badge as evidence against KP1--KP3.

Likewise, the I0 closeout CI `29571586666` / job `87856392726` and correction
CI `29572258679` / job `87858551554` each reported exactly
`10 failed, 2628 passed, 8 skipped, 161 deselected`.  Nine failures are the
known Linux re-solve wire-SHA drift from the frozen Windows MaxEnt result; the
tenth is the old terminal-topology guard observing an intentionally new
sidecar.  All seven published artifacts passed their public strict verifiers.
This is a classified control/portability defect, not a scientific or hard-tier
failure.

## 2. Purpose, claims, and evidence firewall

L0 asks one bounded question:

> On the frozen public-synthetic families, can before-state graph locality
> features rank exact synthetic counterexample queries at least as well as a
> deterministic lexicographic baseline, without merging states, pruning ghost
> actions, or importing nominal information into a hard channel?

L0 may establish only:

* deterministic construction and strict serialization of before-only local
  graph features;
* exact equality or inequality of declared synthetic response vectors;
* monotone separation of one witnessed region pair at a time;
* nominal query-ranking behavior and a paired held-out loss curve; and
* a finite public-synthetic engineering disposition.

Every proposal, learned partition, ranking, curve, and report has
`PipelineEvidenceTier.NOMINAL_DIAGNOSTIC_ONLY` and `hard_eligible == false`.
An exact response inequality may be stored in a dedicated exact-observation
witness, but exactness attaches only to that witnessed pair and response word.
It does not attach to the learner's partition or report.

The new region-pair witness must not reuse `ExactDistinguishingWitness`: that
existing type identifies exact quotient block indices, while L0 witnesses two
declared local-region IDs under one ordered query.  Any independent exact
partition claim must instead start from an `AdmittedExactFiniteSnapshot`, run
the existing exact refinement, and pass `verify_exact_partition` to obtain a
`VerifiedExactPartition`.  The learner has no constructor or converter for
that type.

No-counterexample, equality on the queried word, good held-out loss, and a
bootstrap interval never prove fiber completeness, lumpability, a safety
bound, a hard partition, or absence of return memory.

## 3. Frozen phase topology

The L0 line is a separate nominal side-track:

```text
f1df8dd accepted hard I0 (never moves here)
  |
  A_L0 authority + frozen matrix
  |
  B_L0 control handoff + S0 portability repair
  |
  C_L0 semantic candidate and deterministic evaluation code
  |
  D_L0 result JSON + closeout
```

Registered refs are:

```text
A primary       codex/uprime-u15-l0-authority
A replacement   codex/uprime-u15-l0-authority-a2
B primary       codex/uprime-u15-l0-control-bootstrap
B replacement   codex/uprime-u15-l0-control-bootstrap-a2
accepted L0     codex/uprime-u15-l0-plan
C primary       codex/uprime-u15-l0-candidate
C replacement   codex/uprime-u15-l0-candidate-a2
D primary       codex/uprime-u15-l0-closeout
D replacement   codex/uprime-u15-l0-closeout-a2
```

A is a direct child of `f1df8dd`.  B is a direct child of the accepted A.  C
is a direct child of the accepted B.  D (or its sole replacement) is a direct
child of the accepted C.
Every `-a2` is an alternative direct child of the same accepted predecessor as
its primary attempt; a failed primary is never placed in the chosen ancestry.
Every published attempt ref is immutable: no deletion, rewrite, force-push,
rerun, merge, or cherry-pick.  After a green B CI, `codex/uprime-u15-l0-plan`
is created at the byte-identical B commit.  It advances by fast-forward only
after distinct green C and D CIs.  The hard accepted ref remains at I0.

### Phase A allowlist

```text
docs/experiments/uprime_odlrq_u15_l0_locality_cegar_phase_bundle_amendment_2026-07-17.md
docs/experiments/inputs/uprime_u15_l0_matrix.json
```

### Phase B allowlist

```text
tests/test_odlrq_similarity.py
tests/test_uprime_u2_u4_development.py
tests/test_uprime_u15_l0_identity.py
tests/uprime_u24_guard.py
tests/tier_manifest.json
tools/run_uprime_u2_u4_development_tests.ps1
```

### Phase C allowlist

```text
lean_rgc/odlrq/locality_cegar.py
lean_rgc/odlrq/__init__.py
lean_rgc/evals/uprime_u15_l0_locality_cegar.py
tests/test_odlrq_locality_cegar.py
tests/test_uprime_u15_l0_locality_cegar.py
tests/tier_manifest.json
```

There is deliberately no `local_region.py`: L0 has one consumer, so splitting
the type layer would create a second module without a second use.  A later L1
authority may split it if native-oracle reuse makes that boundary real.

### Phase D allowlist

```text
docs/experiments/uprime_odlrq_u15_l0_locality_cegar_closeout_2026-07-17.md
docs/experiments/artifacts/uprime_odlrq_u15_l0_20260717/locality_cegar_result.json
```

No per-component amendment/execution triplets, custom runner, ledger, CAS,
publisher, recovery coordinator, or capture wrapper may be added.  This one
phase bundle governs B, C, and D.

## 4. Old-epoch handoff and S0 portability repair

B is control bootstrap, not a scientific result.  It makes the historical
U24 identity finite rather than loosening it:

1. verify the complete old U24 chain through I0 `f1df8dd` with its existing
   stage order and identities;
2. preserve `MAX_BUILD_COMMITS = 6` exactly;
3. freeze the I0 commit, tree, parents, and old terminal path blobs as the old
   endpoint;
4. stop the old validator there; and
5. give A--D a new `test_uprime_u15_l0_identity.py` suffix validator.

The old budget is not increased, reinterpreted, or reset inside
`test_uprime_u2_u4_development.py`.  L0's four-phase suffix has its own exact
path and parent checks.  The new identity must accept only the registered
optional A/B/C/D replacement paths and exactly one accepted D terminal path,
never arbitrary history.

The historical static scanner SHA-pins the non-I0 core of
`test_uprime_u2_u4_development.py`, and the existing PowerShell runner and
`uprime_u24_guard.py` mutually bind their normalized source hashes.  An honest
handoff therefore changes those three control files atomically.  B updates the
old identity core, freezes its new hash in the guard, updates only the existing
runner's guard-core binding, and then closes the hash cycle by freezing the new
normalized runner hash in the guard.  The guard continues to check the old
U24 bytes at `f1df8dd` and delegates only the new A--D suffix to the new
identity module.  The existing runner's lanes, limits, denylist, process
behavior, and execution semantics remain byte-for-byte except for the
necessary guard-core binding.  It is not invoked by L0 and no new runner is
created.

B also repairs the nine-platform-failure S0 test fixture without changing S0
semantics.  It reuses the accepted evaluation module's exact 4177-byte
`_ME0_RESULT_JSON`, strictly parses it, round-trips it byte-for-byte, checks the
frozen Windows SHA-256
`DCA363A6C8CC15ED13C4182DE7BFD2F68293E83C1766419B439C1AE8309C42E3`,
and runs the public verifier.  A Linux re-solve may additionally check status,
support, equations, and the already-frozen numeric tolerances, but its wire SHA
must never be compared with the Windows wire SHA.  B may not change solver
code, support, tolerances, reference law, fixture values, or accepted artifact
bytes.

The four exact B tests are:

```text
tests/test_uprime_u15_l0_identity.py::test_u15_l0_frozen_parent_sidecars_and_authority_identity
tests/test_uprime_u15_l0_identity.py::test_u15_l0_old_u24_epoch_is_immutable_and_handoff_is_exact
tests/test_uprime_u15_l0_identity.py::test_u15_l0_phase_suffix_paths_parents_refs_and_budgets_are_exact
tests/test_uprime_u15_l0_identity.py::test_u15_l0_static_scope_tier_firewall_and_terminal_topology
```

They are zero-argument, undecorated, and cannot be replaced by skip, xfail,
parameterization, collection indirection, or plugin behavior.

## 5. Frozen synthetic data model

The implementation may reuse these exact foundations:

```text
ObservationFrameId
BehavioralObservationKey
ActionSymbol
CanonicalPayload
ExactRational
PipelineEvidenceTier
AdmittedExactFiniteSnapshot
VerifiedExactPartition
verify_exact_partition
canonical_contract_bytes
exact_rational_rank
```

`ExactDistinguishingWitness` is explicitly excluded from L0 region-pair
observations.  `action_geometry`, `response_learner`,
`contextual_congruence`, `mvar_blocks`, legacy quotient implementations,
private I0 fixtures, `NominalOperator`, NumPy, and random libraries are not
Phase-C semantic dependencies.  The sole exception is B's test-only import of
the explicitly named frozen `_ME0_RESULT_JSON` for the portability repair in
section 4; it cannot enter `locality_cegar.py` or the L0 evaluation result.

The frozen public L0 surface is:

```text
BeforeLocalRegion
LocalityFeatureVector
LocalityQuery
ExactLocalResponseObservation
ExactLocalCounterexample
ProposedNominalPartition
LocalityQueryScore
LocalityCEGARReport
LocalityResultDisposition
make_before_local_region
extract_before_locality_features
make_locality_query
derive_exact_query_cost
make_exact_local_response_observation
find_exact_local_counterexample
propose_nominal_partition
rank_locality_queries
apply_exact_counterexample_split
run_synthetic_locality_cegar
verify_locality_cegar_report
```

Private helpers are permitted inside `locality_cegar.py`; no other public name
may be exported from `lean_rgc.odlrq` in C.

Each region contains only pre-action data: canonical node kinds, undirected
sharing edges, boundary-port kinds, shared-mvar incidence, target-site kind,
and radius.  The exact feature vector is:

```text
canonical node-kind count rows
canonical boundary-port kind/count rows
sorted shared-mvar degree multiset
sorted component-size profile after separator deletion
articulation-point count
cycle rank = edge_count - node_count + component_count
exact treewidth
radius
target-site kind
```

Canonical first-occurrence numbering and sorted typed rows make the feature
wire invariant under region-node relabeling.  After-state fields, audit
results, carrier dimensions, future outcomes, response values, and held-out
labels are rejected rather than ignored.

Every `SyntheticAction` used by L0 carries a `CanonicalPayload` containing the
complete strict `ActionSymbol` wire.  The outer synthetic `action_id` must
equal the inner symbol `action_id`; ID-only payloads and action splicing reject.
Every frozen action ID starts with the existing admission prefix
`unit_cpu_survivor_u15_l0_`, so the unchanged exact-snapshot admission contract
can accept it.  Phase C may not weaken or bypass that prefix check.
Queries bind an ordered action word and a closing-context ID, not a single
action label.  That ID resolves through the frozen context catalogue to an
ordered closing-action word and response-coordinate order; L0's sole context
has zero closing actions and two ordered response coordinates.  Word and
coordinate order are semantic.

The action catalogue includes `ghost_store` and `reveal`.  `ghost_store` has a
zero direct one-step response in the ghost family, while the ordered word
`ghost_store,reveal` has a nonzero return response.  Direct no-op behavior may
not prune an action.  Removing the ghost action changes the complete catalogue
digest and invalidates every query/report binding.

## 6. Exact observations and monotone CEGAR

The initial proposed partition groups regions by the complete frozen
before-feature vector.  It is nominal.  A query returns a declared exact
rational response vector for each covered region.  An exact local
counterexample consists of:

```text
observation frame and transition-semantics identities
complete action-catalogue digest
complete ordered query wire
two canonical region IDs in one current block
the two unequal exact response vectors
the exact first differing coordinate
admitted snapshot digest and verified-partition certificate digest
the two resolved terminal state IDs and their distinct verified block indices
```

Cross-frame, cross-semantics, cross-catalogue, or cross-query splicing rejects.
The verified exact partition ranges over composite snapshot states, not bare
region IDs.  For each `(instance, region, query)` row, the frozen projection
resolves its terminal state and records that state's verified block index.
The terminal-block signature of a region is the ordered vector of those block
indices over the complete query catalogue.  A declared region block is
accepted as exact ground truth only when all members have equal signatures and
different declared blocks have different signatures.  Source, intermediate,
closed, and sink states never project to region IDs.  No region partition is
accepted from naked response rows or from a hand-written block list alone.
When a counterexample verifies, the pair becomes a must-not-link edge and the
lexicographically larger endpoint is isolated from its current block.  Thus
the new partition strictly refines the old partition and separates exactly the
witnessed pair; it does not assign an exact label to any unwitnessed pair.
Existing must-not-link edges are never removed.

An equality observation or absence of a counterexample leaves the partition
unchanged.  There is no public merge operation.  Neither case promotes the
partition, feature, query, or report.  At the end of the locality schedule,
every frozen seeded pair on all 24 instances (eight train and 16 held-out) must
be separated in the instance's final partition.  An available seed that remains
co-blocked at `t = 16` is an exact learner miss and forces `DEGRADED`; it is
never rewritten as a prerequisite block, abstention, or no-clear result.
Observing a different candidate that happens to separate the seeded pair is
sufficient, because the endpoint is separation rather than literal selection
of the seed's query.
L0's verified region projection is defined relative to the same complete query
catalogue, so this phase cannot diagnose query-language inadequacy without
circularity.  That question is deferred to an L1 authority with an independent
Lean-oracle witness language.

## 7. Exact covariance objective and query cost

For each region `i` and query `q`, `y_i(q)` is the query's ordered two-coordinate
exact response.  The global evaluation vector is the canonical concatenation
of all eight query responses in matrix query-catalogue order and closing-context
coordinate order:

```text
Y_i = y_i(q_0) || y_i(q_1) || ... || y_i(q_7) in Q^16
```

For a proposed partition `P` of `n` regions, construct the full 16-by-16
conditional covariance matrix of `Y_i` using rational arithmetic.  This global
vector defines both checkpoint loss and candidate gain, so losses at different
queries and at `t=0` are comparable.  The candidate query's own two-coordinate
response is used only to decide whether that candidate witnesses a split:

```text
mean_C     = (1 / |C|) sum_{i in C} Y_i
Sigma(P)   = (1 / n) sum_{C in P} sum_{i in C}
             (Y_i - mean_C) (Y_i - mean_C)^T
V(P)       = trace(Sigma(P))
Delta(c)   = V(P) - V(P refined by exact candidate c=(pair,q))
J(c)       = Delta(c) / cost(c)
```

The complete 16-by-16 covariance matrix, not a diagonal or per-query surrogate,
is computed and recomputed by the verifier.  To respect the result-wire cap,
each score/checkpoint row serializes its canonical covariance SHA-256 and exact
trace together with the bound partition, rather than duplicating all 256 cells.
The verifier reconstructs every cell before accepting the digest and trace.
All arithmetic uses `Fraction`/`ExactRational`; binary floating point is
forbidden in scoring.

One ranked candidate is the canonical unordered region pair together with one
complete query wire.  The pair is encoded by its two region IDs in ascending
canonical-byte order.  Observing one candidate consumes exactly one budget
step; observing the same query on a different pair is a different candidate.

For the queried region pair `R`, query word `w`, closing-action word `z`
resolved from the frozen context catalogue, and response arity `d`, cost is
mechanically derived as:

```text
cost(q,R) = |R| * (|w| + |z| + d)
```

It is a positive integer.  Wall time, caller-supplied costs, profiler output,
and post-outcome cost changes are forbidden.  Ranking order is:

```text
J descending, derived cost ascending, canonical full candidate bytes ascending
```

The lexicographic baseline uses the same final full-candidate bytes.  Query
bytes alone are not a total ordering and may not be used as a tie-break.

The locality schedule is greedy and adaptive on the train carrier only.  Start
at the before-feature partition `P_0`.  At each step recompute `J(c | P_t)` for
every unobserved candidate, choose the frozen tie-break maximum, read that
candidate's two-coordinate train response, apply its verified monotone split
when unequal within a current block (otherwise leave the partition unchanged),
remove the candidate, and repeat.  Scores are recomputed after every step.  A
one-shot sort at `P_0`, held-out feedback, and candidate reuse are forbidden.
The baseline is the nonadaptive canonical full-candidate byte order.

## 8. Frozen matrix, caps, and fail-closed behavior

The companion matrix has exactly these eight named families:

```text
separator_rank0
separator_rank1
separator_rank2
delayed_effect
ghost_memory
noncommutativity
bisimilar
relabel
```

Every family has one fixed train instance and two fixed held-out instances.
All three share the same declared action/query universe, initial-partition
rule, query budget, and response schema.  They carry three complete,
instance-specific response tables; held-out tables are not uniform rescalings
or mechanically derivable transforms of the train table.

The evaluation loader strictly parses the whole frozen matrix, then constructs
disjoint immutable train and held-out carriers.  The ranker accepts only the
train carrier.  For every family it returns and hashes a complete ordered
candidate schedule before the held-out carrier can be opened.  Opening a
held-out table before the complete eight-family map containing both methods'
schedule digests is sealed is
`CONTRACT_FAIL`.  Direct matrix dictionaries, held-out response rows, or an
evaluation carrier are invalid ranker inputs.  Family membership,
train/held-out role, and all denominators are fixed before C exists.

Hard pre-materialization caps are:

```text
families                         8 exactly
instances per family             3 exactly (one train, two heldout)
query catalogue                  <= 16
action word depth                <= 3
oracle response cells             <= 256 per instance
snapshot totalized states         <= 128 per instance
snapshot transition rows          <= 2048 per instance
regions                          <= 16 per instance
nodes                            <= 12 per region
undirected edges                 <= 24 per region
exact treewidth                  <= 8 per region
response coordinates             <= 8 per row
global behavior coordinates       = 16 exactly
identifier UTF-8 bytes           <= 128
input rational bits              <= 256
intermediate rational bits       <= 4096
wire bytes                       <= 1 MiB per object
JSON depth / array / keys         <= 16 / 256 / 64
```

Exact treewidth is computed by deterministic subset dynamic programming only
after the node/edge cap checks.  The order is strict: construct both schedules
from train data only; seal the complete two-method/eight-family schedule-digest
map; only then open and admit the held-out carriers and construct and seal the
exact `P_0` partition, full covariance, covariance digest, and trace loss for
all 16 held-out instances; only then may either method consume its first
held-out evaluation candidate.
Any frozen-fixture cap, schema, kind, admission, response, censor, or resource
failure that prevents this global `P_0` barrier is
`PREREQUISITE_BLOCKED`, because no exact last-defined denominator value exists.
This includes a frozen fixture whose mechanically required state/row bound
exceeds its own declared global cap.

Within the fixed paired evaluation, `ABSTAIN` is reachable only after that
global `P_0` barrier.  A later stage-resource failure retains the instance's
last exact partition, covariance, and loss in the fixed denominator.  The
public locality API may also return `ABSTAIN` for an unseen runtime input that
exceeds a declared cap, but such a call is outside this frozen 16-instance
paired denominator and cannot affect L0's disposition.  Normal completion at
budget step 16 and the short-universe plateau in section 9 are not abstentions.
Attempting a 17th candidate observation or repeating a candidate is
`CONTRACT_FAIL`.  An available seeded distinguisher left co-blocked at `t = 16`
is a learner miss and forces `DEGRADED`.  The implementation must not truncate,
approximate, drop a family, or substitute a nominal value.  Leakage of future
data, a nonmonotone split, ghost pruning, tier conversion, digest mismatch, or
malformed strict wire is `CONTRACT_FAIL`, never abstention.

## 9. Family-stratified paired evaluation

The locality ranker and deterministic lexicographic baseline receive the same
training instances, initial partition, ordered candidate universe, and budget.
After both train-only schedules and their global digest map are sealed, but
before either schedule is applied to held-out evaluation, the evaluator must
pass the global exact `P_0` barrier defined in section 8.  Consequently every
denominator member has an exact loss at `t = 0`; there is no imputation,
nominal substitute, zero-fill, or undefined "last value" at the first checkpoint.
The baseline orders canonical full-candidate bytes and uses no locality score.
Each method freezes, per family, the first
`min(16, unique candidate-universe cardinality)` candidates without repetition.
Held-out responses are read only after all schedules and their digests are
frozen in memory.

Both methods are evaluated at every integer budget step `t = 0,...,16`; one
candidate observation advances one step.  The reporting subset is
`0, 1, 2, 4, 8, 16`.  At those checkpoints record for every held-out instance
and its family aggregate:

```text
canonical full-covariance SHA-256 (all cells verifier-recomputed)
exact trace loss V(P)
coverage numerator and fixed denominator
abstention count and reason
censor count and reason
candidate observations consumed and cumulative exact derived cost
```

If a family exhausts its unique candidate universe before step 16, later
values are right-padded with its final partition, loss, and cumulative cost.
`UNIVERSE_EXHAUSTED_PLATEAU` is neither abstention nor censor, does not reduce
coverage, and never repeats or fabricates a candidate.

For method `m`, family `f`, and held-out instance `i`, let `L_f,i^m(t)` be that
instance's exact trace loss after `t` candidates.  Aggregation is fixed as:

```text
Sigma_f^m(t) = (Sigma_f,alpha^m(t) + Sigma_f,beta^m(t)) / 2 elementwise
L_f^m(t) = (L_f,alpha^m(t) + L_f,beta^m(t)) / 2
L^m(t)   = (1 / 8) sum_f L_f^m(t)
         = (1 / 16) sum_{all held-out instances i} L_i^m(t)
```

The family covariance digest binds that elementwise exact mean and is verifier
recomputed; it is not a covariance of pooled region members.  Region members
are never pooled across instances or families.  A post-`P_0` abstained instance
retains its last exact partition/covariance/loss and remains in the 16-instance
denominator.  The frozen matrix contains no censors; any censor that prevents
`P_0` is a prerequisite block, and after the complete response table has sealed
`P_0` no later censor can be introduced.  Coverage numerator, abstention count,
and the zero-checked censor count are reported over that same denominator.

The exact area uses the unit budget axis and the left-rectangle convention over
the complete curve, not the sparse reporting checkpoints or cumulative cost:

```text
AULC(m)    = sum_{t=0}^{15} L^m(t)
Delta_AULC = AULC(baseline) - AULC(locality)
```

The gain gate requires `L^locality(t) <= L^baseline(t)` for every
`t = 0,...,16`, equal coverage numerators, equal censor counts, no greater
locality abstention count, strict loss improvement at at least one `t`, and
separation by `t = 16` of every frozen seeded pair on all eight train and 16
held-out instances under the locality schedule.
The no-clear branch requires the same seed-completeness condition.  All 16
held-out instances and all eight family aggregates remain in every denominator.
No selective-family, pooled-member, or complete-case denominator is allowed.

A family-cluster bootstrap with 10,000 replicates is reported as a nominal
diagnostic only.  Resampling is by whole family, uses a SHA-256 counter stream
from the matrix's fixed seed, and reports the percentile interval for paired
family `Delta_AULC_f = sum_{t=0}^{15}(L_f^baseline(t)-L_f^locality(t))`, with
the eight sampled families equally weighted.  For replicate `r=0,...,9999`
and draw `k=0,...,7`, hash the exact UTF-8 string
`u15-l0-bootstrap-v1|<decimal seed>|<decimal r>|<decimal k>`, interpret the
first eight digest bytes as an unsigned big-endian integer, and take modulo 8
as the sampled family index into the matrix's
`fixed_denominator_family_ids` array in its frozen array order.  Sort the
10,000 exact rational replicate means;
the two-sided diagnostic endpoints are zero-based order statistics 249 and
9749.  No PRNG library, float, interpolation, or alternate percentile rule is
allowed.  With eight families it is not an inferential gate, cannot
override the deterministic primary, and cannot enter a hard channel.

## 10. Result sum type and downstream license

The D result has exactly one of:

```text
L0_SYNTHETIC_CEGAR_GAIN_OBSERVED
L0_SYNTHETIC_CEGAR_NO_CLEAR_GAIN
L0_SYNTHETIC_CEGAR_DEGRADED
L0_PREREQUISITE_BLOCKED
L0_EXECUTION_FAILED
```

`GAIN_OBSERVED` requires the deterministic gate in section 9 and all contract
tests.  `NO_CLEAR_GAIN` is a valid complete, seed-complete run with no
deterministic strict gain and no degradation; it carries diagnostic
`L0_STRUCTURAL_HEURISTIC_NOT_SUPPORTED`.  `DEGRADED` is reachable whenever a
frozen checkpoint is worse, coverage falls, abstention rises, or any frozen
seeded pair remains co-blocked under the locality schedule at `t = 16`.
`PREREQUISITE_BLOCKED` covers cap, matrix, admission, response, censor, or
resource prerequisites that prevent the exact global `P_0` barrier;
`EXECUTION_FAILED` covers an incomplete or invalid run.  All five branches are
tested and reachable; no branch is silently rewritten into gain.

Only `GAIN_OBSERVED` licenses drafting, not executing, a separate native Lean
oracle L1 authority.  `NO_CLEAR_GAIN` or `DEGRADED` does not refute the
upper-stack theory.  It blocks L1 under this feature/query design and requires
a newly frozen rational design before further learning.

## 11. Exact C tests

The 16 core tests are:

```text
tests/test_odlrq_locality_cegar.py::test_l0_before_region_features_are_relabel_invariant_and_exact
tests/test_odlrq_locality_cegar.py::test_l0_path_cycle_articulation_and_treewidth_features_are_known
tests/test_odlrq_locality_cegar.py::test_l0_after_audit_carrier_and_future_features_are_rejected
tests/test_odlrq_locality_cegar.py::test_l0_query_binds_complete_ordered_action_symbols_and_cost
tests/test_odlrq_locality_cegar.py::test_l0_cross_frame_query_and_response_splicing_reject
tests/test_odlrq_locality_cegar.py::test_l0_exact_counterexample_adds_must_separate_and_splits_monotonically
tests/test_odlrq_locality_cegar.py::test_l0_equality_and_no_counterexample_never_merge_or_promote
tests/test_odlrq_locality_cegar.py::test_l0_proposal_and_report_remain_nominal_and_hard_ineligible
tests/test_odlrq_locality_cegar.py::test_l0_ghost_noop_is_retained_by_delayed_return_witness
tests/test_odlrq_locality_cegar.py::test_l0_ghost_omission_changes_catalog_digest_and_rejects
tests/test_odlrq_locality_cegar.py::test_l0_full_conditional_covariance_reduction_is_exact_fraction
tests/test_odlrq_locality_cegar.py::test_l0_query_cost_reverses_ranking_and_tie_break_is_canonical
tests/test_odlrq_locality_cegar.py::test_l0_caps_apply_before_materialization_and_abstain
tests/test_odlrq_locality_cegar.py::test_l0_exact_partition_requires_independent_verifier
tests/test_odlrq_locality_cegar.py::test_l0_wire_caps_mutations_and_duplicate_keys_fail_closed
tests/test_odlrq_locality_cegar.py::test_l0_public_surface_has_no_merge_hard_promotion_or_forbidden_import
```

The four evaluation tests are:

```text
tests/test_uprime_u15_l0_locality_cegar.py::test_u15_l0_matrix_identity_families_and_seeded_witnesses_are_exact
tests/test_uprime_u15_l0_locality_cegar.py::test_u15_l0_family_stratified_paired_curves_use_fixed_denominator
tests/test_uprime_u15_l0_locality_cegar.py::test_u15_l0_dispositions_cover_gain_no_gain_degraded_blocked_and_failed
tests/test_uprime_u15_l0_locality_cegar.py::test_u15_l0_repeated_evaluation_is_byte_identical_and_budget_bound
```

All 20 are zero-argument, undecorated, non-parameterized tests with no skip,
xfail, deselection, hidden plugin, network, process, native Lean, or test-helper
import substitution.  The eval module may construct only the frozen synthetic
matrix and public L0 objects.

The disposition test must additionally exercise the operative seed rule: a
strictly verified available seeded pair left co-blocked by the locality prefix
at `t = 16` recomputes to `DEGRADED`, while both gain and no-clear reject a
non-seed-complete report.  It must also prove that a paired run cannot classify
a pre-`P_0` failure as denominator-retaining abstention.

The fourth evaluation test is also the conditional D verifier without adding a
test node.  At C, both Phase-D paths must be absent.  At D, both must be present:
it strict-parses the result, recomputes it from the accepted C source and frozen
matrix, requires canonical byte equality, verifies every public report, and
checks the closeout's C commit/tree, matrix blob, result SHA-256, disposition,
counts, and resource receipt.  Presence of only one path, extra artifact files,
or a closeout/result mismatch fails CI.  Thus an arbitrary D JSON cannot inherit
the unchanged 2662-test count.

## 12. Qualification, CI gates, and resource budget

Development and qualification are Windows CPU only.  Natural repository CI is
the only remote execution.  No SSH, GPU, LLM, network, native Lean RPC, R13
wrapper/calibration, official transport, or protected endpoint is licensed.

Direct commands use `C:\Python313\python.exe`, pytest plugin autoload disabled,
`PYTHONHASHSEED=0`, and no bytecode/cache output.  There is no persisted runner.

```text
# B identity
python -m pytest -q -p no:cacheprovider tests/test_uprime_u15_l0_identity.py
# C locality
python -m pytest -q -p no:cacheprovider tests/test_odlrq_locality_cegar.py tests/test_uprime_u15_l0_locality_cegar.py
# old typed integration
python -m pytest -q -p no:cacheprovider tests/test_odlrq_similarity.py tests/test_uprime_u2_u4_development.py
# small exact regressions (the 6132 exhaustive node is deselected)
python -m pytest -q -p no:cacheprovider tests/test_odlrq_behavioral_partition.py tests/test_odlrq_history_normal_form.py tests/test_odlrq_hankel_depth4.py -k "not exhaustive_6132"
```

B requires exactly `4 passed` for its identity file.  C requires exactly
`20 passed` for its two L0 files.  The stage-local L0 command has a 120-second
wall.  The combined targeted qualification has a 300-second wall, 2-GiB peak
RSS ceiling, and 1-MiB combined-output ceiling.  Exceeding a ceiling blocks
publication and triggers algorithmic simplification inside the allowlist; it
does not license a runner or control framework.  The 6132-family exhaustive
M3/D4 test and native Lean suites are not rerun in this phase.

A has no scientific test and may have only one of these natural-CI shapes:

```text
1 failed, 2637 passed, 8 skipped, 161 deselected
10 failed, 2628 passed, 8 skipped, 161 deselected
```

The first is the expected old terminal-topology failure.  The second adds only
the nine predeclared S0 Linux MaxEnt wire-SHA failures.  Any other node or count
blocks B.  A red badge of either exact shape is an authority control result,
not an L0 result.

After B's handoff and portability repair, both the B attempt-ref CI and the
distinct accepted-L0-ref CI on the byte-identical B commit must be green with
exactly `2642 passed, 8 skipped, 161 deselected`.  Natural C candidate CI and
the distinct accepted-L0 CI must be green with exactly
`2662 passed, 8 skipped, 161 deselected`.  D adds no test, so its natural CI
and final accepted-L0 CI must have the same green count.  Full repository CI
is run once per ref publication; the attempt ref and accepted ref intentionally
produce distinct runs on the same SHA.  No failed run is manually rerun to
obtain a favorable sample.

## 13. Anti-fractal repair and stop rules

A, B, C, and D each have one primary and at most one `-a2` publication attempt.
A2 may correct only document/matrix identity, ordering, or result-totality
defects found by the final pre-source audit before B source; it may not change
the frozen responses, features, action/query/family catalogues, endpoint values,
or evidence tier.  B2 may correct only the six Phase-B control paths.  C2 may
correct only the six semantic paths without changing the matrix, public
meaning, evidence tier, caps, denominators, query universe, or result rule.  D2
may correct only the two Phase-D paths and must deterministically regenerate the
same result semantics from the same accepted C and matrix; it cannot change a
disposition to obtain a green result.  A failed ref stays immutable.

Ordinary code defects, serializer mistakes, wrong graph orientation, stale
hashes, CI count mistakes, platform fixture drift, and resource overruns are
implementation problems, not theoretical stop conditions.  They are repaired
autonomously within the current allowlist and bounded attempts.  Exhausting an
attempt budget produces a concise rational-remedy report for Fable and a fresh
pre-source authority if a rational repair exists.  User direction is requested
only if the project-wide theory is refuted or no rational repair remains.

The following are outside this authority:

```text
changes to f1df8dd or the hard accepted ref
changes to E0/E1/E2/ME0/S0/I0 source or seven I0 artifacts
hard-tier flow, safety promotion, or absence-of-counterexample promotion
protected/reserved tasks, pilot_tasks.json, or llm_local.json
native Lean, RPC, R13 wrapper work, official transport, or K-series reruns
occurrence-rw or macro-tactic implementation
production action_geometry integration
memory/safety L1 queries or rank-one separator correction
parallelization, continuousization, or gradientization
SSH, GPU, LLM, external network, or proposer training/distillation
ledger, CAS, publisher, recovery coordinator, or new runner infrastructure
```

Untracked user files in the main checkout are neither read nor moved.  LLM
distillation remains last: only after the theoretical generator is strictly
validated and resources remain may a separate authority ask whether LLM
knowledge can be distilled into it.

## 14. Pre-freeze adversarial implementation review

Independent agents attacked the missing implementation plan rather than
repeating the 2026-07-10 theory review.  They covered the mathematics-to-code
map, repository reuse, branch governance, endpoint reachability, tier
firewall, paired evaluation, and anti-fractal repair budget.  Their blocking
draft findings were incorporated here:

* the learner cannot reuse the exact quotient block-pair witness;
* exact partition claims require the existing admitted-snapshot verifier path;
* a full inner `ActionSymbol` wire and outer/inner ID equality are mandatory;
* every family needs one train and two held-out instances;
* deterministic paired AULC/noninferiority is primary, while the eight-family
  bootstrap is diagnostic only;
* ghost-return behavior prevents direct-no-op pruning;
* S0 portability must verify frozen Windows bytes and not compare a Linux
  re-solve SHA; and
* all gain, no-clear-gain, and degraded branches must be reachable.

No theoretical stop condition was found.  Primary A was classified with its
exact predeclared CI shape but rejected for the two pre-source ambiguities
recorded above.  The approved next action is A2 freeze, exact A2-CI
classification, then B control bootstrap.  Source C must not begin before B is
green.

Because L0 is public-synthetic development rather than a protected endpoint,
the final mechanics audit also evaluated the frozen recurrence before source C
existed.  It predicts `L0_SYNTHETIC_CEGAR_DEGRADED`: locality is worse than the
baseline at `t = 5,...,16`, and two `separator_rank2` held-out seeds remain
co-blocked at `t = 16` (`heldout_alpha`: `sr2_zero/sr2_one` under `q_b_a`;
`heldout_beta`: the same pair under `q_ghost_store_reveal`).  This disclosure is
part of the design audit, not a blind scientific look.  C and D test strict
recomputation, serialization, and disposition conformance; they must not market
the already-predicted synthetic disposition as new empirical evidence.
