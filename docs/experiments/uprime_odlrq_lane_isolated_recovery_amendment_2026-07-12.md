# U-prime / ODLRQ lane-isolated recovery and upper-stack transfer amendment

Date: 2026-07-12 (Asia/Tokyo)

Status: **FROZEN ONLY WHEN THE EXACT FOUR-PATH AMENDMENT COMMIT IS COMMITTED,
PUSHED, AND GREEN.**  This is a genuinely new phase after the closed
CPU-survivor bundle.  It does not extend that bundle, retry its registered
runner, or reclassify its resource-stop disposition.

## 1. Authority, immutable predecessor, and scientific-result adjudication

The sole parent of the amendment commit is the immutable closeout commit

```text
92b34496d3f2455a63e05791b7a0342050c49bcd
```

The qualified exact finite partition dependency remains milestone M3 at

```text
ec7275d18755331285dc1b9ac4e9b5ccfbe13f17
```

The following M3 blobs are immutable throughout this phase:

| path | Git blob |
|---|---|
| `lean_rgc/odlrq/contracts.py` | `eca7d55bc7c2a7a08fbdc75c3b589f1972cd258f` |
| `lean_rgc/odlrq/adapters.py` | `12b46d6418c69fd842b347a24ec783e5de052b76` |
| `lean_rgc/odlrq/behavioral_partition.py` | `0f6e961b5158b5bc684898d6ee2740427d9a689e` |
| `tests/test_odlrq_behavioral_partition.py` | `7b500bac52051744cd0032b5af8bfc1b64c30aed` |

The closeout at the parent remains `CLOSED BY THE FROZEN RESOURCE STOP RULE`.
Its discarded, uncommitted WP6-T candidate is neither a result nor an input.
The three defects learned before/after that stop are engineering requirements
for a clean reimplementation in this new phase; they are not evidence that the
discarded candidate passed.

### 2026-07-12 control-plane clarification retained for future readers

The immutable U05 result-publication commit has red GitHub Actions run
`29166670576` (job `86580832840`).  The
dated audits identify the cause as the identity guard's shallow-history design
omission, not a probe, prerequisite, artifact-integrity, or scientific-result
failure.  The exact scientific candidate had green GitHub Actions run
`29166073728` (job `86579287017`).  The red result badge therefore must not be
read as a failed scientific execution.  The consumed look, result values,
result commit, and rerun prohibition remain unchanged.

## 2. Corrected objective and phase boundary

The objective is not another evidence-ledger layer.  It is to complete the
small finite substrate that the upper construction actually needs, then return
to the original program:

```text
immutable exact finite partition (M3)
  -> M4 exact/certified/observed/nominal tier firewall
  -> M5 bounded rational predictive realization
  -> M6 componentwise finite-memory diagnostic
  -> Lean-specific canonical-history feasibility probe
       +-> hard track: exact quotient coordinates
       |     -> finite-horizon positive worst-case envelope
       |     -> MaxEnt nominal law inside that envelope
       |     -> finite-approximation-stable predictive/positive similarity
       +-> nominal query track: Lean-oracle locality CEGAR L0
             -> memory/safety CEGAR L1 only after the hard upper objects exist
  -> later parallel / continuous / gradient phases
  -> protected evaluation only under a filled Amendment A
```

This phase implements only M4, M5, and M6 on local Windows CPU.  The three
lanes have separate runners, resource budgets, commits, and dispositions.  A
failure in one lane does not block the other two, except that M4 is explicitly
blocked if the immutable M3 dependency is unavailable or changed.

No protected task, U05 artifact payload, canonical RPC input, LLM, GPU, SSH,
native Lean process, production selector, or new evidence-ledger/CAS subsystem
is an input to this phase.

## 3. External theory provenance: design antecedent, never Lean evidence

The following UTF-8 source and experiment archive were inspected on
2026-07-12:

| external source | bytes | SHA-256 |
|---|---:|---|
| `fiber_closure_generator_part2_jp.tex` | 50,796 | `FED9A116D04E56D41FC6A306B1C85CA85399B92375322ED45EED546E4FE126A7` |
| `fiber_closure_generator_part2_experiments.zip` | 3,675,760 | `1FA90B92C0998FAEC941F658BA295B34790568924022A068EFC2CA03C69C95E2` |

The archive contained no absolute or parent-traversal member.  From the safely
extracted directory
`experiments/18_arbitrary_depth_motif_generator`, the command
`python -m unittest -v test_motif_generator.py` was reproduced once on local
Windows CPU as an external-code check: `8 tests`, `OK`, `43.072 s`.  The key
source hashes were `BA41777212F8F7EE2B0A7F11C16F27FEDA56F47EE655BEE40A211A773F8D5FEE`
for `motif_core.py`,
`F97D622EC1E467BB486C86D63429F17843DC19981ADCA8543668972F31B4721E`
for `motif_iteration.py`, and
`3567C8963592060A92FA247CFE75E04B2A7C0F5DA3930C35DBB72F3EC68D7B9A`
for `test_motif_generator.py`.  That run and every NS-side number are
provenance only.  They are not a Lean threshold, fixture, endpoint, ground
truth, or completion certificate.

The completed finite-support patterns registered for later transfer are:

1. generation-time normal-form reduction rather than materializing every tree
   history and reducing afterwards;
2. first-order closure of every coordinate under a derivation as the NS finite
   induction base for arbitrary Lie-derivative depth on that declared support;
3. exact normalization and quotient before any positive majorant;
4. retention of direct-inactive but return-memory-active (ghost) primitives;
5. separator-aware correction instead of naive addition of local quotients;
6. exact symbolic structure separated from floating diagnostics or fitting.

The following are not completed transferable facts: arbitrary-support/cutoff
library completeness or minimality, infinite-cutoff uniform control, full
physical coefficient injection, a Lean action-word congruence, a Lean
treewidth/rank bound, universal rank-one separator correction, packed/orbit/AD
engineering, or any NS norm/rank/history-count threshold.

Most importantly, the NS motif algebra is commutative while Lean action words
are generally noncommutative.  A generation-time rewrite may identify two Lean
histories only after an exact, typed witness proves preservation of the
registered response for every admitted continuation.  Words such as `a;b` and
`b;a` are never merged from a commutative analogy alone.

The four root scratch files previously discussed are already absent from the
repository and present on the repository-external shelf
`$HOME/.codex/quarantine/lean-rgc/uprime-deferred-2026-07-12/`.  This phase does
not move them again, parse them, create a manifest for them, or add them to an
EvidenceLedger.  LLM proposal/distillation remains outside the loop until the
exact generator and upper stack work without it.

## 4. Mathematics-to-code traceability

### 4.1 Current recovery lanes

| obligation | implementation owner | executable witness |
|---|---|---|
| verified exact finite quotient source | immutable `behavioral_partition.VerifiedExactPartition` | retained M3 blobs and hosted CI; small source-bound fixtures only, not the 6,132-system rerun |
| exact quotient export | new `quotient_generator.ExactFiniteOperator` | construction only from a reverified `VerifiedExactPartition`; complete member/action rows |
| independently certified interval | new `UppernessDomainWitness` and `CertifiedIntervalOperator` | exact successor contained for every block/action; domain/source bindings; undercoverage kill |
| evidence-tier separation | `ExactFiniteOperator`, `CertifiedIntervalOperator`, `ObservedIntervalOperator`, `NominalOperator` | allowed and forbidden conversion tests; no observed/nominal promotion or envelope constructor |
| semantic Hankel cell | new `hankel_predictive.ResponseAtomKey` | `(task_id, concatenated_action_word, channel)` aliases all prefix/suffix splits of one response |
| training-only rational realization | `TrainingHankelView`, `BoundedRationalRealization` | exact rank/basis from the frozen training capability; complete read footprint; target-read sentinel |
| honest predictive endpoint | `PredictiveResidualReport` | nonempty disjoint targets, coverage/abstention, exact max/L1/per-channel residual and terminal ablation |
| componentwise finite-memory population | new `componentwise_window` module | occurrence and immutable-state denominators; existential/universal continuations; transient overshoot |

The old `lean_rgc/odlrq/hankel.py` remains the historical U05 cutoff probe.  M5
uses the new `hankel_predictive.py` module so an exact development realization
cannot be confused with the earlier aggregate rank diagnostic.

### 4.2 Registered later transfers

| transferred idea | future code owner | prerequisite executable witness |
|---|---|---|
| Lean history normal form | `history_normal_form.py`, `rule_algebra.py`, `reachable_chart.py` | typed rewrite witness, reconstruction, idempotence, continuation congruence, noncommutation kills, depth-at-most-3 raw/normalized response equality |
| first-order closure induction | `behavioral_partition.py`, later generator checker | a separate Lean induction proves that response homogeneity plus all-action stability implies all-word stability on a complete declared finite domain; this is not inferred from the NS derivation |
| quotient before positive envelope | `quotient_generator.py` then `envelope.py` | no raw/observed/nominal hard-envelope path; fiber extension cannot reduce an upper bound |
| ghost primitive retention | `rule_algebra.py`, `componentwise_window.py`, `locality_cegar.py` | one-step no-op separated by a two-step continuation; classify `direct_active`, `memory_only`, `unresolved`, never prune by class |
| separator correction | `local_region.py`, `locality_cegar.py` | naive local sum kill; 0/1/2 shared-constraint fixtures measure correction rank instead of assuming rank one |
| exact/float split | `hankel_predictive.py`, later `maxent.py` | rational rank/basis/certificate only; float conditioning/nominal optimization has no hard-tier constructor |
| parallelization | later shard runner | exact symmetry equivariance, serial/sharded canonical-byte equality, shard-order invariance, separator-boundary kill |
| continuousization | later `continuous_generator.py` | on a finite quotient, `L = sum_a lambda_a (P_a-I)` plus semigroup/Poissonization tests; no unproved identification with the NS polynomial derivation |
| gradientization | later nominal `maxent.py` / `locality_cegar.py` | frozen measure/target and conditional-covariance loss; exact structure is stop-gradient and no-counterexample never promotes exactness |

## 5. M4 / WP6-T: tier firewall reimplementation

M4 consumes the immutable M3 object and reimplements, rather than recovers, the
discarded candidate.  Its public construction graph is exactly:

```text
VerifiedExactPartition
  -> ExactFiniteOperator

ExactFiniteOperator
  + externally supplied interval candidate
  + independently supplied UppernessDomainWitness
  -> CertifiedIntervalOperator
```

`ObservedIntervalOperator` and `NominalOperator` are standalone, nonpromotable
schemas.  This phase adds no `FiberEnvelope`, no public helper that fabricates
upperness evidence, and no conversion from observed or nominal objects to exact
or certified objects.  It also adds no convenience conversion from exact or
certified objects into observed/nominal objects: every tier is constructed from
its own explicit provenance so a conversion cannot silently shed authority.

All three repairs learned from the closed bundle are mandatory:

1. **Serializer rederivation.** `ExactFiniteOperator`,
   `UppernessDomainWitness`, and `CertifiedIntervalOperator` retain their
   authority-bearing source objects.  Every `to_dict()` reverifies and
   rederives visible fields from those sources.  Low-level mutation may not be
   serialized; a mismatch raises.  `from_dict()` requires the relevant external
   authority and accepts only byte-for-byte equality with the rederived wire.
2. **Signed-64 interval targets.** Every target block index satisfies
   `type(x) is int` and `0 <= x <= 2^63-1`.  Booleans, negative values, and
   larger integers fail before tuple/set normalization.
3. **Preallocation cap.** Let `M_total` be the sum of all quotient-block member
   counts, including every `OPEN`, `CLOSED`, and `SINK` totalized state; let `B`
   be the number of quotient blocks, `A` the number of actions, `T` the sum of proposed
   target-list lengths, and `U` the sum of the per-row union sizes between each
   proposal and its exact-successor singleton.  The exact frozen formula is
   `W_T = M_total*A + B*A + T + U`.  Checked multiplication/addition must establish
   `W_T <= 250,000` before a second table, set, or output tuple is built.
   Wire-shape caps and `T` are checked before decoding nested target values.

Mandatory attacks include direct/subclass construction, `object.__setattr__`
mutation, unknown fields, source/certificate mismatch, representative-action
substitution, missing block/member/action, interval undercoverage, interval
shrinkage, bool/negative/huge targets, and a combined-work preallocation bomb.

M4 qualifies only as `CPU_TIER_FIREWALL_VERIFIED`; it does not construct a
production certified interval or claim a complete Lean fiber.

## 6. M5 / WP4-H: bounded rational predictive realization

M5 is independent of M4 and consumes only declared exact rational response
atoms on deterministic synthetic fixtures.  Rows and columns are semantic
keys, never integer positions.  All aliases of one response use

```text
ResponseAtomKey(task_id, prefix + suffix, channel).
```

Targets are declared before fitting.  `TrainingHankelView` is a capability,
not an eager full table: it exposes only registered training atoms and records
every read used for rank discovery, rejected pivots, the core cross `C`, task
initial rows `alpha`, shifted action matrices `A_a`, and channel columns
`beta`.  A target-atom read during fitting raises immediately.

The channel taxonomy is frozen before targets: every channel key carries one
class from `nonterminal`, `closed_terminal`, or `sink_terminal`, and the
taxonomy digest is bound into the table, training view, target declaration,
realization, and residual report.  An ablation is therefore a typed projection,
not a post-hoc relabeling.

The exact training rank and deterministic lexicographic full-rank cross are
computed with rational arithmetic.  Coefficients and residuals remain exact;
floating SVD may be reported only as conditioning diagnostics and cannot choose
rank, basis, endpoint, or disposition.  Missing shifts, missing prefix closure,
censors, cap overflow, or coefficient growth blocks construction rather than
returning a partial model.

Structural caps are checked before allocation/read: at most 512 semantic rows,
512 semantic columns, 250,000 cells, rank 64, 1,000,000 total UTF-8 key bytes,
and 8,192 bits in every intermediate or final numerator/denominator.  Before
response reads, the caller freezes `r_cap` with
`1 <= r_cap <= min(64,nr,nc)`.  Here `nr` and `nc` are the declared training
row/column counts, `na` is the action count, `nt` the task count,
`nc_channels` the channel count, `n_targets` the declared target count, and
`max_target_word_length` the declared maximum target word length.  The
additional conservative rational-work preflight is

```text
W_H_pre = nr*nc*min(nr,nc)
        + (na+1)*r_cap^3
        + (nt+nc_channels)*r_cap^2
        + n_targets*r_cap^2*max(1,max_target_word_length)
    <= 2,000,000.
```

The declared `r_cap` is frozen before reads, so every product and sum in
`W_H_pre` is available before any response read.  Training-only reduction then
computes `r_train`, requires `r_train <= r_cap`, and uses `r_train` for the
realization and per-operation coefficient-bit checks while targets remain
unread.  These combined caps, not the rectangular maxima in isolation, define
the qualified envelope;
a near-envelope rejection fixture verifies the preflight without requiring a
slow near-cap solve.  Tests also cover low-rank exact reproduction, split
aliasing, nonempty held-out residuals, terminal/nonterminal channel ablations,
permutation canonicality, adversarial mutation, incomplete shifts, and target
read leakage.

M5 qualifies only as `CPU_HANKEL_PREDICTIVE_CORE_VERIFIED`.  Exact arithmetic
on a synthetic development table is not hard Lean evidence.

## 7. M6 / WP4-W: componentwise-window diagnostic

M6 freezes task seeds, the prefix-closed occurrence universe through
`D_start=4`, and continuation horizon `K=4`.  Reverse dynamic programming
computes whether an open state can close within each remaining horizon without
first entering `SINK`.

A registered continuation is nonempty, remains open at every prefix including
its endpoint, and its endpoint can still close within the remaining budget.
Immediate terminal closure therefore creates no open-to-open block.  The report
keeps two denominators:

1. occurrences keyed by `(task_id, start_word)`; and
2. unique immutable states, with existential and universal continuation
   statements reported separately.

Contraction is coordinatewise nonincrease with at least one strict decrease.
For every continuation and coordinate, transient overshoot is the maximum
positive increase over every intermediate prefix; endpoint contraction cannot
erase it.  Population overshoot includes contracting and noncontracting
continuations.  Exactly five coordinates are required and `zip`-style silent
truncation is forbidden.

Tests cover expand-then-contract, good-versus-bad continuation, many words to
one state, immediate terminal nonmanufacture, equality without strict decrease,
K+1 unresolved, overshoot, ordering, coordinate mismatch, and rejection of
censor/non-`NOT_APPLICABLE` synthetic oracle fields.

M6 qualifies only as `CPU_COMPONENTWISE_DIAGNOSTIC_VERIFIED`.

Every task seed is an explicit synthetic `(task_id, state_id)` binding to one
revalidated admitted snapshot.  Before generating words, checked integer
arithmetic computes the raw upper bounds
`S = n_seeds*sum_(d=0)^D_start A^d` and
`P = S*sum_(k=1)^K A^k`.  The lane requires `S <= 100,000`,
`P <= 250,000`, `P*(K+1) <= 2,000,000` transition work units, and at most
64 MiB canonical report bytes.  A cap failure blocks before occurrence or
continuation materialization; observed pruning is never used to evade the
preflight.

## 8. Dedicated runners and frozen resource margins

Each argumentless, self-contained Windows PowerShell runner selects exactly one
semantic test module and embeds its own fixed test path and budget.  Each owns
safe path resolution, a fresh system temporary directory, subprocess denial
inside semantic tests, UTF-8 capture, 2 GiB parent working-set cap, 64 MiB
output cap, process termination, and owned temporary cleanup.  No runner can
accept a caller-selected test path or budget.  Deliberate duplication preserves
lane independence if any earlier runner is never accepted.

| lane | runner | frozen test | hard wall | mandatory 3x qualification margin |
|---|---|---|---:|---:|
| M4 / WP6-T | `tools/run_uprime_wp6_t_recovery_tests.ps1` | `tests/test_odlrq_quotient_generator.py` | 30 s | elapsed at most 10 s |
| M5 / WP4-H | `tools/run_uprime_wp4_h_recovery_tests.ps1` | `tests/test_odlrq_hankel_predictive.py` | 60 s | elapsed at most 20 s |
| M6 / WP4-W | `tools/run_uprime_wp4_w_recovery_tests.ps1` | `tests/test_odlrq_componentwise_window.py` | 30 s | elapsed at most 10 s |

M4's last registered lane-only diagnostic was 1.89 seconds, so its 30-second
wall is over fifteen times that observation.  M5 and M6 had no prior
implementation.  Their walls are not tuned after seeing results: the runner
itself fails the lane if `3 * elapsed > hard_wall`, even when the process
finishes before the hard wall.  A wall or margin failure is a lane resource
block, not a semantic counterexample.

The exhaustive 6,132-system M3 suite, identity guard, and manifest suite are not
repeated inside any lane runner.  M3 integrity is supplied by the immutable
commit/blobs above, its recorded hosted CI, source-bound small lane fixtures,
and the ordinary full hosted CI for each committed descendant.

Execution is local Windows CPU only.  Network use is limited to normal Git
push and read-only hosted-CI status/log inspection.  No SSH/GPU phase is
licensed here.

## 9. Exact path allowlists and commit topology

The amendment commit changes exactly:

```text
docs/experiments/uprime_odlrq_lane_isolated_recovery_amendment_2026-07-12.md
tests/test_odlrq_lane_isolated_recovery_identity.py
tests/tier_manifest.json
.github/workflows/ci.yml
```

The workflow change is restricted to `actions/checkout@v4` with
`fetch-depth: 0` and explicit pull-request head-SHA checkout; a synthetic PR
merge commit is not treated as a single-parent scientific candidate.  The
identity guard rejects shallow repositories; it never substitutes a weaker
depth-one proof.  The manifest change preserves every existing row and adds
only the new identity test as `unit`.

M4 may change only:

```text
lean_rgc/odlrq/__init__.py
lean_rgc/odlrq/quotient_generator.py
tests/test_odlrq_quotient_generator.py
tools/run_uprime_wp6_t_recovery_tests.ps1
tests/tier_manifest.json
```

M5 may change only:

```text
lean_rgc/odlrq/__init__.py
lean_rgc/odlrq/hankel_predictive.py
tests/test_odlrq_hankel_predictive.py
tools/run_uprime_wp4_h_recovery_tests.ps1
tests/tier_manifest.json
```

M6 may change only:

```text
lean_rgc/odlrq/__init__.py
lean_rgc/odlrq/componentwise_window.py
tests/test_odlrq_componentwise_window.py
tools/run_uprime_wp4_w_recovery_tests.ps1
tests/tier_manifest.json
```

The consolidated closeout changes exactly one new closeout document.  The
identity guard is immutable after the amendment and already knows the exact
closeout path/topology.  No M3 file, old monolithic CPU runner, U05 result/evaluator,
external review/source, root scratch input, native Lean/RPC file, production
pipeline, further CI workflow, evidence ledger, CAS, or publication subsystem
is in a semantic allowlist.

Let `A_recovery` be the amendment commit.  It is the exact four-path,
single-parent child of `92b34496...` and must be pushed and hosted-CI green
before M4 begins.  Each lane then owns one planned semantic commit and at most
one same-lane hosted-CI repair commit.  Quota is not transferable.  The
identity test is not in a semantic allowlist and every accepted descendant must
retain its exact `A_recovery` blob.

Each lane candidate branch starts from the current accepted head.  Local lane
runner success precedes its first candidate commit.  Up to two same-lane
commits are pushed to that candidate branch.  Only a hosted-CI-green candidate
may fast-forward the accepted `codex/uprime-odlrq-plan` line.  If the two-commit
quota is exhausted, the rejected branch hash/run remains diagnostic evidence,
the accepted line is unchanged, and the next independent lane starts from that
accepted head.  Thus a red candidate cannot poison later lanes.  Every accepted
milestone is then pushed on the accepted line before the next lane begins.
Deterministic unit tests are covered by this bundle and do not receive per-test
preregistration documents.

The accepted implementation interval contains at most six single-parent,
non-merge semantic commits in nondecreasing M4, M5, M6 order, with at most two
per lane and no mixed-lane commit.  It is followed by at most one one-path
closeout commit, which must be last.  The identity guard enforces each lane's
allowlist, manifest-only append semantics, order/quota, immutable amendment
test, prior U05/closeout blobs, and exact final closeout topology using full Git
history with replacement objects disabled.  Once the unique closeout exists,
the guard fixes the phase head at that commit, freezes the closeout blob, and
permits later descendants to be governed by their own amendments; it does not
freeze M3 or the recovery allowlist across all future work.
No amendment/result triplets, ledger extensions, or synthetic publisher
apparatus are created.

## 10. Independent dispositions and stop rules

Each lane closes with exactly one of:

```text
CPU_TIER_FIREWALL_VERIFIED
CPU_HANKEL_PREDICTIVE_CORE_VERIFIED
CPU_COMPONENTWISE_DIAGNOSTIC_VERIFIED
CPU_RECOVERY_PREREQUISITE_BLOCKED
CPU_RECOVERY_LANE_FAILED
```

M4 may additionally use `CPU_RECOVERY_M3_DEPENDENCY_BLOCKED`.  A lane-local
wall, 3x margin, RSS/output cap, construction cap, serializer integrity,
allowlist, or two-commit exhaustion stops only that lane.  M5 and M6 continue
and are reported independently.  No scalar portfolio pass is reported.

The whole phase stops only if an immutable M3/result/closeout blob would change,
a protected or excluded input would be read, a path escapes the union
allowlist, the total commit budget is exceeded, or work would require SSH, GPU,
LLM, native Lean/RPC, a second U05 look, or a new evidence-governance subsystem.

The following are explicitly forbidden recurrences: recombining all lanes into
the 300-second monolithic runner; rerunning M3 exhaustive qualification in each
lane; serializing mutable cached fields; allowing a certified object to create
its own independent evidence; checking caps only after allocation; propagating
one lane's resource failure to unrelated lanes; promoting the U05 Hankel
diagnostic; or importing depth-4 NS work into this recovery interval.

## 11. Next phase candidate: name and obligations only

The next candidate is registered by name only:

```text
U'1.5-KP3-D4-CANONICAL-HISTORY
provenance: fiber_closure_generator_part2
```

The word `orbit` is deliberately absent until an exact group action or rewrite
congruence is proved.  This registration grants no implementation, execution,
cap change, protected read, or claim authority.  A fresh committed, pushed, and
green amendment must freeze:

1. the Lean-specific ordered rewrite grammar and witness type;
2. preservation under every registered continuation;
3. generation-time normalization, multiplicity, and provenance invariants;
4. reconstruction, idempotence, and adversarial noncommutation tests;
5. complete depth-at-most-3 raw versus normalized response equality;
6. response channels, task seeds, word/Hankel caps, wall/RSS, and stop rules;
7. a dimension preflight that does not assume compression.

For orientation only, twelve actions and five tasks give 113,105 raw word
occurrences through depth four, and a common depth-four Hankel layout would have
785 by 1,099 = 862,715 cells.  Those figures exceed the present caps.  Depth
four may run only after the registered preflight and exact regression succeed;
the NS compression ratio is never used to waive a cap.

## 12. Upper-stack implementation sequence after recovery

### 12.1 Two noninterchangeable tracks

After the canonical-history feasibility phase, a separate `U'1.5-L0`
amendment may build only a congruence/separator CEGAR MVP.  Before-only features
propose nominal merges or boundary variables.  Exact Lean counterexamples force
splits; absence of a counterexample remains statistical.  Ghost actions remain
in the primitive alphabet.  The task/query matrix, proper loss, query-cost
denominator, coverage/abstention, baseline, seed/tie-break, censor policy, and
held-out grouping are frozen before a learner pilot.  Memory/safety acquisition
is a later `U'1.5-L1` substage after the upper operators exist.

`U'1.5-L0` is a nominal proposal/query track, not a dependency or authority for
the hard track.  The hard track independently proceeds from verified exact
quotient coordinates through envelope, MaxEnt, and similarity.  Only after
those objects exist may `U'1.5-L1` ask memory/safety questions.  No learner
merge constructs an exact partition or hard upper bound.

### 12.2 U'2--U'4 CPU development construction

One later bundle, using only synthetic or already-contaminated inputs, proceeds
in this noninterchangeable order:

```text
ordered exact symbols
  -> a Lean-specific normalizer independently verified continuation-congruent
     on its complete declared domain
  -> exact behavioral quotient
  -> quotient-coordinate generator
  -> positive finite-horizon worst-case majorant
  -> MaxEnt nominal law constrained inside the majorant
  -> predictive and positive global similarities with R/N/G transports
```

The hard envelope accepts only a complete frozen finite fiber or an
independently certified upper superset.  It is built on quotient coordinates,
after exact duplicate/cancellation removal, but signed cancellation is never a
safety argument.  Fiber extension is monotone.  The envelope controls safety;
MaxEnt is model selection inside its admissible support.  Predictive distance
and positive-safety distance are distinct types.  Global similarity carries
node and edge measures, coverage, true-target residual, and typed radius,
word-depth, and granularity morphisms with an explicit approximation remainder.

Only after the serial CPU reference is green may three separate amendments
consider, in order: separator/symmetry-aware **parallelization**, finite-quotient
Poisson **continuousization**, and nominal-only **gradientization**.  Serial and
sharded canonical bytes must agree before performance claims.  Exact structure,
hard upperness, and certificate decisions remain CPU-rechecked and outside the
gradient.

### 12.3 Amendment A skeleton

No placeholder below is authority.  A future filled Amendment A must replace
every item with a concrete committed value before protected K-series work,
deployment, remote construction, or GPU work:

```text
candidate commit / tree / source and dependency blobs: UNFILLED
ObservationFrameId / PolicySemanticsId / toolchain hashes: UNFILLED
TransitionSemanticsId / ReachableDomainId: UNFILLED
normalizer and rewrite-system digest / continuation-congruence witness: UNFILLED
complete finite domain or independently certified upper-superset witness: UNFILLED
action grammar, totalization, target routing, replay, cap, and censor semantics: UNFILLED
Lambda / R / N / G schedule and refinement/look budgets: UNFILLED
K1 compression, K2 envelope, K3 Hankel, K4 similarity endpoints and kill rules: UNFILLED
envelope horizon, weights, first/second moment and return-memory bounds: UNFILLED
MaxEnt reference law, statistics, target, support, KL radius, proper-score baseline: UNFILLED
predictive/positive metrics, true-target residual, coverage, approximation remainder: UNFILLED
learner class, loss, query families, seed/tie-break, split policy, baseline: UNFILLED
task strata, sample size, power/MDE, multiplicity, missing/censor rules: UNFILLED
protected read/scorer custody, append-only exposure protocol, external adjudication: UNFILLED
CPU/GPU commands, host key, environment/model hashes, wall/RAM/VRAM/disk/retry caps: UNFILLED
paired all-task U'5 solve-rate denominator and co-primary coverage/abstention/cost: UNFILLED
```

GPU is expected only for a later large learned representation/acquisition model.
It does not compute exact partitions or hard certificates.  LLM distillation is
even later: only after the theory-driven generator and upper pipeline work, and
only under a separate amendment freezing weights, tokenizer, runtime,
quantization, prompt, sampler, seed, concurrency, and contamination strata.

## 13. Mandatory nonclaims

This amendment licenses no protected K1--K4 result, depth-four result,
production Lean locality claim, complete all-germ quotient, hard fiber envelope,
MaxEnt fit, global-similarity certificate, learner improvement, solve-rate
claim, deployment, SSH/GPU work, or LLM proposer/distillation.  A verified lane
is exact only relative to its declared finite synthetic development semantics.
NS completion labels and numerical results never transfer as Lean evidence.

## 14. Adversarial implementation-plan review disposition

The 2026-07-10 47-agent review of the upper theory is not repeated.  This
document instead incorporates two independent implementation-plan attacks:

1. a recovery/governance reviewer attacked lane coupling, wall calibration,
   cap placement, serializer authority, commit topology, and the temptation to
   rerun M3 inside every runner; and
2. an NS-transfer reviewer attacked completion overclaim, commutative-to-
   noncommutative transport, assumed compression, ghost pruning, universal
   rank-one correction, and exact/float tier leakage.

The first concrete draft was rejected by all three reviewers.  Confirmed defects
were: missing tier-manifest registration; a shallow-history proof gap identical
in kind to the prior control-plane accident; a self-modifiable union-only
identity guard; an undeclared shared-runner dependency; ambiguous failed-CI
lineage; implementation-defined work caps; and underspecified M5 channel/M6
enumeration bounds.  The corrections above make CI full-history, freeze the
guard after amendment, enforce lane-specific topology, make runners
self-contained, keep rejected candidates off the accepted line, and define the
missing formulas/types.

After those repairs, all three reviewers independently returned **APPROVE** on
the final pass.  They rechecked the exact four paths, full-history/PR-head CI,
lane classifier and quotas, candidate isolation, one-path phase closeout,
`M_total` and `r_cap` work formulas, M6 preflight, and the NS transfer boundary.
Local identity/manifest verification was `6 passed`.  The final disposition is
therefore **APPROVE TO FREEZE THIS EXACT BOUNDED M4--M6 RECOVERY PHASE**.
Approval does not extend to the named next phase or upper-stack executions.
