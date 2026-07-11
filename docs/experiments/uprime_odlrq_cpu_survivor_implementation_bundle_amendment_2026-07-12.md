# U' CPU-survivor implementation-bundle amendment

Date: 2026-07-12 JST

Status: **FROZEN WHEN COMMITTED AND PUSHED GREEN.** The commit containing this
document is the temporal anchor for this development-only bundle. It is a new
phase after the immutable U05 result; it does not amend, rerun, or reinterpret
that one-look execution. It licenses only the bounded Windows-CPU work named
below.

## 1. Authority and immutable predecessor

The governing implementation roadmap is
`docs/experiments/uprime_odlrq_upper_stack_implementation_plan_and_u05_amendment_2026-07-11.md`,
introduced by commit `0da9ff3de91819778761fb087e85e6f83e4c9ea4` with Git
blob `2b2355f49aef149c1a7b5493951fa10e4a254235`.

The final U05 execution candidate was
`3bb3408afc50a08307cff2c9b1906a299739dfb5`. Its sole-child result-publication
commit is `cc91a4181a9f87ec10f11727ed787eb7149f955a`. That result commit changed
exactly four regular files:

| path | Git blob |
|---|---|
| `docs/experiments/artifacts/uprime_u05_20260711/u05_kill_probes.json` | `33061cffae56abf4ed2a4fcdb9400eb2004e61c6` |
| `docs/experiments/uprime_odlrq_u05_execution_2026-07-11.md` | `724f8c426aa71de62c1f0837f36077133e64ca6f` |
| `lean_rgc/evals/uprime_rpc_litmus.py` | `2bbc052a2afa954b46090dcdcf2ec082d8e9a1a4` |
| `tests/test_uprime_rerun_license.py` | `9f1e20e742aa3c53cd779a1ca392e870a7e15477` |

The outer artifact is canonical, has SHA-256
`75BD0F4A742FD7F5DA221FD629DA58F080FD17CB0ACE9BFC8150153D8FDB55F8`,
and records `runner_complete`, `U05_COMPLETE`, and `look_consumed=true`. The
canonical rerun registry remains empty and default-deny. This bundle must not
modify any of those four result paths, the candidate, receipt, raw child,
matrix-open marker, or artifact. A second U05 matrix open is prohibited.

### 2026-07-12 control-plane adjudication

The result-publication commit has a red GitHub Actions run `29166670576`, job
`86580832840`. The immutable log contains exactly one failing test,
`test_first_implementation_commit_freezes_exact_plan_anchor_topology`; the
remaining result was `2340 passed, 7 skipped, 161 deselected`. In the hosted
depth-one checkout the plan commit was unavailable, and the fallback guard
incorrectly required the current `lean_rgc/evals/uprime_rpc_litmus.py` blob to
remain the plan-era blob `9f6d89c3109e8c98520137aee201e79d39858b23`, even though
the frozen four-path result topology required the result blob
`2bbc052a2afa954b46090dcdcf2ec082d8e9a1a4`.

The scientific execution candidate had green GitHub Actions run `29166073728`,
job `86579287017`, at exact head
`3bb3408afc50a08307cff2c9b1906a299739dfb5`. Independent result adjudication,
envelope-integrity, result-commit-guard, shallow-CI, pytest-topology, and
governance-recovery audits agree on the disposition: **the red result CI is a
control-plane shallow-history guard design omission, not a probe,
prerequisite, artifact-integrity, or scientific-result failure.** The consumed
look, result values, immutable result commit, and rerun prohibition are
unchanged. This amendment repairs the guard in its own new phase; it does not
rewrite history or manufacture a green result commit.

## 2. Capability selection and independent dispositions

The U05 capability matrix permits drafting three development candidates:

| lane | U05 disposition | selected work | endpoint |
|---|---|---|---|
| `WP4-E` | `U05_KP1_SCALE_READY` | synthetic exact finite Moore partition and independent verifier | `CPU_EXACT_PARTITION_CORE_VERIFIED` |
| `WP4-H` | `U05_KP3_PLATEAU_AT_D3` | bounded rational Hankel cross predictor with explicit training footprint and residual | `CPU_HANKEL_PREDICTIVE_CORE_VERIFIED` |
| `WP4-W` | `U05_KP2_EVENTUAL_WINDOW` | componentwise-window witness and honest occurrence/state accounting | `CPU_COMPONENTWISE_DIAGNOSTIC_VERIFIED` |
| `WP6-T` | depends on `WP4-E` | exact/interval/observed/nominal tier firewall and exact quotient export | `CPU_TIER_FIREWALL_VERIFIED` |

These lanes are adjudicated separately. Failure of one lane neither kills nor
licenses another, except for the registered dependency `WP4-E -> WP6-T`: an
`WP4-E` failure blocks `WP6-T`. The common-admission gate blocks all four lanes;
`WP4-H` and `WP4-W` otherwise remain independent. There is no scalar portfolio
pass. The dependency graph is:

```text
common admission --+--> WP4-E --> WP6-T
                   +--> WP4-H
                   +--> WP4-W
```

The U05 observations do not supply their implementation ground truth:

- KP1 measured repeated full state identities, not behavioral merges between
  distinct states.
- the depth-bounded run recorded one frontier discard, so its transported chart
  is not a complete all-action domain;
- the artifact contains aggregate KP2/KP3 reports, not the original transition
  chart, Hankel cells, or trajectory population;
- `U05ProbeTransition` is explicitly nonpromotable and lacks complete M3
  locality evidence; and
- the existing `ReachableChart` view does not retain every cap, replay, delta,
  coverage, and boundary field needed for hard admission.

Therefore the result artifact is provenance only. No lane consumes its
embedded task statements, transitions, matrices, or aggregate values as
training data, and no lane reconstructs or reruns the U05 matrix.

## 3. Scope relative to the upper-stack objective

The intended upper pipeline remains:

```text
exact finite generator and tier firewall
-> independently certified finite-horizon worst-case upper operator
-> MaxEnt nominal law constrained inside that hard operator
-> finite-approximation-stable predictive and positive global similarity
-> Lean-oracle locality CEGAR
-> protected paired evaluation
```

This bundle implements and verifies only the first line's finite development
substrate plus the two surviving diagnostic lanes. The worst-case envelope
must still precede MaxEnt, and MaxEnt remains model selection rather than a
safety source. Predictive similarity and positive-safety similarity remain
different types. Locality learning remains a later `U'1.5-L` phase: exact Lean
counterexamples may eventually split proposals, while absence of a
counterexample never promotes a merge to exact.

## 4. LLM-outside-the-loop and local quarantine

The exact generator, its independent verifier, the tier firewall, and later
Lean-oracle locality mechanism must be made to work without any LLM proposer.
Only after those components and their upper-operator consumers have independent
CPU evidence, and only if resources remain, may a separate proposer/distillation
amendment ask whether model knowledge can be distilled into the nominal
proposal layer. Such a future amendment must freeze `PolicySemanticsId`, model
weights, tokenizer, runtime, quantization, prompt, sampler/seed, concurrency,
and pretraining-contamination strata. An LLM may never supply kernel
transitions, exact partitions, hard upper bounds, or evidence tier.

After this amendment is pushed and green, the following four untracked root
files are moved individually with literal paths, without parsing or importing
their contents, to the repository-external local quarantine shelf
`$HOME/.codex/quarantine/lean-rgc/uprime-deferred-2026-07-12/`:

| basename | classification after quarantine |
|---|---|
| `llm_local.json` | deferred, unsealed proposer configuration; not a `PolicySemanticsId` |
| `pilot_tasks.json` | public/pretraining-contamination-unresolved; permanently ineligible for U'5 |
| `fake_lean_smoke.py` | noncanonical scratch harness; never imported or executed |
| `smoke_tasks_local.jsonl` | unregistered scratch tasks; never a task source |

Administrative byte-preservation checks are not scientific evidence and do not
enter an EvidenceLedger, exposure marker, dataset, manifest, or endpoint. No
new ledger, CAS, publisher, recovery, or quarantine subsystem is created. Tests
and implementation use no repository-root glob and must fail if any excluded
basename is proposed as an input.

## 5. Development input contract

All positive semantic inputs are source-embedded deterministic fixtures whose
IDs begin `unit_cpu_survivor_`. No production U05 task ID is permitted. No
fixture reads a repository task file, the result artifact, a legacy quotient,
an LLM/model file, or a protected/reserved dataset.

An exact object in this phase means exact only relative to a fully declared,
finite, synthetic transition system and response vocabulary. It is not an
exact statement about all Lean states, all germs, all contexts, or a production
reachable domain.

Every admitted positive input carries the nonerasable profile
`evidence_scope=synthetic_development`. In that profile, Lean-only fields
`target_binding`, `delta`, `replay`, `cap`, and `M3` are exactly
`NOT_APPLICABLE`; fixtures may not fabricate oracle evidence. Only finite-table
construction completeness is exact. A `lean_exact` profile and every positive
adapter from `ExactKernelTransitionCore`, `U05ProbeTransition`, or
`ReachableChart` are unimplemented and forbidden in this bundle. The evidence
scope remains in every certificate and operator serialization.

The common finite snapshot must freeze:

- a domain ID, response-vocabulary ID, frame ID, and transition-semantics ID;
- complete, unique state and action payloads (not IDs alone);
- a total transition row for every state/action pair;
- explicit absorbing `CLOSED` and `SINK` behavior, with the mandatory response
  key `(totalized_kind, registered_coordinates)` so success and ordinary
  failure cannot merge even when user coordinates agree;
- exact integer/rational responses with a fixed coordinate schema;
- censor, truncation, boundary, live-handle, queued-state, and outside-domain
  absence; and
- canonical bytes independent of input enumeration order.

The admission gate rejects incomplete rows, duplicate payloads, action-ID
collisions, external successors, mixed frames/semantics, any Lean-only field
other than `NOT_APPLICABLE` in the synthetic profile, censors, or any
`ExactKernelTransitionCore`/`U05ProbeTransition`/`ReachableChart` promotion. M3
locality is `NOT_APPLICABLE` only because `locality_claim=false`; requesting a
locality claim or stripping the evidence scope is an error.

## 6. Mathematics-to-code map

| mathematical obligation | implementation owner | executable witness |
|---|---|---|
| finite declared domain and exact admission | `contracts.py`, `adapters.py` | strict full table, typed IDs, canonical bytes, prohibited conversions |
| totalized finite Moore system | `behavioral_partition.py` | every state/action has exactly one successor; `CLOSED`/`SINK` absorb |
| initial response partition | `behavioral_partition.py` | exact response equality under one frozen vocabulary |
| monotone congruence refinement | `behavioral_partition.refine_exact_partition` | split trace terminates within `|Q|-1` strict rounds |
| coarsest response congruence | `ExactPartitionCertificate` and independent verifier | response/action stability plus shortest lexicographic distinguishing word for every distinct block pair |
| structural quotient transition | `behavioral_partition.py` | all representatives agree for every action; representative-substitution kill fixture |
| tiered operator export | `quotient_generator.py` | accepts only a verified structural quotient and preserves its evidence scope |
| exact/certified/observed/nominal separation | `quotient_generator.py` | allowed-conversion and forbidden-conversion tests; no observed/nominal promotion |
| bounded Hankel table | `hankel.py` | keyed rows/columns, immutable values, prefix/shift completeness, cell cap before construction |
| rational realization | `hankel.py` | lexicographic training-only basis, exact core inverse, action matrices, and frozen training footprint |
| predictive endpoint | `PredictiveResidualReport` | disjoint target cells, coverage/abstention, exact max/L1/per-channel residual; no float decision |
| componentwise window | `componentwise_window.py` | occurrence and immutable-state denominators; existential/universal continuation distinction |
| transient expansion | `componentwise_window.py` | intermediate coordinate peak and unresolved-at-K accounting |

### 6.1 WP4-E exact finite partition

For a sorted action alphabet `A`, initialize blocks by exact registered response
and refine by

```text
signature_k(x) = (response(x), (block_k(tau_a(x)))_{a in A}).
```

Canonical block numbering uses complete member payloads, never a hash alone.
The independent verifier recomputes closure, every refinement step, final
stability, quotient well-definedness, and pairwise distinguishing words.
Stability alone is insufficient because the identity partition is always
stable.

Required fixed fixtures include a bisimilar diamond, a delayed separator,
`CLOSED` versus `SINK` with identical user coordinates, action asymmetry,
response perturbation, state/action
permutations, and negative admission cases. A structurally independent brute
force solver must agree for all 6,132 deterministic binary-output automata with
`1 <= n_states <= 3` and `1 <= n_actions <= 2`. A 64-state/12-action fixture
checks structural work counters without a timing-based pass condition.

### 6.2 WP6-T tier firewall

`ExactFiniteOperator` is constructible only from a verified complete finite
chart and partition certificate. `CertifiedIntervalOperator` additionally
requires an independent upperness/domain witness. `ObservedIntervalOperator`
and `NominalOperator` are separate, nonpromotable types. This phase may build
strict schemas, verifiers, round trips, and synthetic fixtures, but it does not
construct a production certified interval or nominal law.

There is no function from observed/nominal to exact/certified. There is no
`FiberEnvelope` constructor in this bundle. Adding a concrete transition must
not silently shrink an interval. A mismatched representative action, interval
undercoverage, missing block member, or unknown field fails closed.

### 6.3 WP4-H bounded rational predictor

Rows and columns are semantic keys, not integer positions. Every response is
also keyed by the split-invariant
`ResponseAtomKey(task_id, concatenated_action_word, channel)`, so different
prefix/suffix decompositions of the same response cannot cross the training/
target boundary. Fitting accepts a capability-restricted `TrainingHankelView`,
never an eager table exposing target atoms. Its exact rank is
`r_train = rank(training-only masked view)`; it never uses the full-table rank,
the U05 rank, or target values. Basis selection chooses the lexicographically
first exact-rational full-rank cross inside that view. If `B_r` and `B_c` are
the selected basis rows and columns, this bundle uses

```text
C       = H[B_r, B_c]
alpha_t = H[(t, epsilon), B_c] C^-1
A_a     = H[B_r . a, B_c] C^-1
beta_c  = H[B_r, (epsilon, c)]
prediction(t,w,c) = alpha_t A_w beta_c.
```

Every fit-time response-atom read belongs to a machine-recorded training
footprint, including rank discovery, rejected pivots, `C`, `alpha`, every
shifted `A`, and `beta`. Targets are declared before fitting and are disjoint
from that footprint by `ResponseAtomKey`, not merely by matrix position. The
report includes target count, prediction count, abstentions, max/L1 error,
exact-match fraction, per-channel residual, nonterminal coverage, and
terminal-only ablations. Floating SVD is diagnostic only and may not select
rank, basis, endpoint, or disposition.

The model is named `BoundedRationalRealization`, not `ExactFiniteOperator`.
Exact arithmetic over a development matrix does not create hard Lean evidence.
Missing shifts, censors, incomplete prefix closure, cap overflow, coefficient
growth, or any target read during fitting blocks model construction rather than
returning a partial predictor.

### 6.4 WP4-W componentwise-window diagnostic

The window analyzer freezes task seeds, a prefix-closed occurrence universe of
all action words of length at most `D_start=4`, and a continuation horizon
`K=4`. For an open start state `s`, `CanClose_h(s)` is computed by exact reverse
dynamic programming and means that some word of length at most `h` reaches
`CLOSED` without first entering `SINK`. A registered continuation `v` has
`1 <= |v| <= K`, remains open at every prefix including its endpoint, and its
endpoint satisfies `CanClose_(K-|v|)`. Thus it is an open-to-open block on a
registered closing path; immediate terminal close creates no such block.

The analyzer keeps two populations:

1. occurrences keyed by `(task_id, start_word)`; and
2. unique immutable states, with existential and universal continuation
   statements reported separately.

It records the minimum resolving window, unresolved starts, all registered
continuations considered, intermediate coordinate peaks, and per-task counts.
Existential means at least one registered continuation contracts; universal
means every registered continuation in the nonempty frozen population
contracts. For coordinate `i`, continuation overshoot is exactly
`max_(0<=j<=|v|) max(D_i(s_(t+j))-D_i(s_t),0)`. Witnesses retain their own
vector, while population overshoot is the coordinatewise maximum over every
registered continuation, contracting or not. Endpoint contraction cannot erase
transient overshoot. Equality without at least one strict coordinate decrease
is noncontractive. Immediate terminal close and derived absorbing extensions
cannot manufacture a window or multiply evidence. Five-coordinate length is
checked explicitly; `zip` truncation is forbidden.

## 7. Exact source and test allowlist

The amendment commit itself changes exactly two paths:

```text
docs/experiments/uprime_odlrq_cpu_survivor_implementation_bundle_amendment_2026-07-12.md
tests/test_uprime_u05_identity.py
```

The contiguous implementation interval may change only:

```text
lean_rgc/odlrq/__init__.py
lean_rgc/odlrq/contracts.py
lean_rgc/odlrq/adapters.py
lean_rgc/odlrq/behavioral_partition.py
lean_rgc/odlrq/quotient_generator.py
lean_rgc/odlrq/hankel.py
lean_rgc/odlrq/componentwise_window.py
tools/run_uprime_cpu_survivor_tests.ps1
tests/test_odlrq_behavioral_partition.py
tests/test_odlrq_quotient_generator.py
tests/test_odlrq_hankel_predictive.py
tests/test_odlrq_componentwise_window.py
tests/test_uprime_u05_identity.py
tests/tier_manifest.json
```

No native Lean, RPC, U05 runner/evaluator, result path, legacy quotient,
production runner, evidence-ledger, CI workflow, root input, or external review
file is in the allowlist.

## 8. Commit topology and milestone order

Let `A_cpu` be the amendment commit and `C_cpu` the final implementation head.
`A_cpu` has `cc91a4181a9f87ec10f11727ed787eb7149f955a` as its sole parent,
changes exactly the two amendment paths above, and must be pushed and green
before semantic implementation begins.

`A_cpu..C_cpu` is a contiguous first-parent interval of at most six
single-parent, non-merge implementation commits. Every repair consumes the same
six-commit budget. The common/WP4-E lane owns at most three commits, WP6-T owns
at most one, WP4-H owns at most one, and WP4-W plus cross-lane integration owns
at most one. A fourth WP4-E commit is forbidden; unused lane quota is not
transferable. The planned milestones are:

1. common IDs, immutable finite snapshot, admission gate, and prohibited
   adapters;
2. exact refinement, certificate, quotient table, and independent verifier;
3. exhaustive/permutation/adversarial WP4-E hardening;
4. tier schemas, exact quotient export, and conversion firewall;
5. keyed Hankel table, training footprint, rational realization, and residual;
6. componentwise-window population analysis plus cross-lane integration.

Each milestone is committed and pushed. Its targeted tests and hosted CI must
be green before the next milestone starts. Component-level preregistration or
result triplets are prohibited. After the interval, at most one consolidated
closeout commit records the four lane-qualified dispositions/reasons and exact
commit/test/resource evidence. It has `C_cpu` as sole parent and changes
exactly:

```text
docs/experiments/uprime_odlrq_cpu_survivor_implementation_bundle_closeout_2026-07-12.md
tests/test_uprime_u05_identity.py
```

The first implementation commit updates `tests/test_uprime_u05_identity.py`
once more to freeze the now-known `A_cpu` commit and its two tree entries. That
edit is part of milestone 1 and consumes the same six-commit/path budget; it is
not a separate governance phase.

The amendment's identity guard fixes both histories without weakening them:
full-history precommit/postcommit checks prove the exact amendment/result diffs;
the amendment's depth-one CI can prove only its raw parent, document blob,
regular test path, and immutable result blobs retained in the current tree
because the parent tree is unavailable. Milestone 1 freezes the known
amendment commit for subsequent descendants. No guard may fetch history, skip
the test, monkeypatch Git, write Git objects, or amend/force-push the result.

## 9. Resource limits

- execution platform: local Windows CPU only;
- implementation commits: at most six;
- external network: only normal Git push and read-only hosted-CI status/logs;
- no SSH, GPU, CUDA, model server, native Lean subprocess, or production RPC;
- the local hard wall/RSS owner is
  `tools/run_uprime_cpu_survivor_tests.ps1`; it launches only the four frozen
  CPU-survivor test modules, rejects arguments, polls the single Python process,
  and terminates/fails at 300 seconds or 2 GiB working set. The semantic tests
  are forbidden to spawn subprocesses. Hosted CI reruns the same modules under
  its ordinary runner; its wall/RSS are corroboration, not the local cap owner;
- exact finite chart: at most 128 totalized states (therefore at most 126
  nonterminal concrete states), 16 actions, and
  `n_totalized_states*n_actions <= 2,048` transition rows;
- Hankel: at most 512 rows, 512 columns, 250,000 cells, and exact rank 64;
- rational numerator/denominator bit length: at most 8,192;
- window length: at most 4;
- word occurrences: at most 100,000;
- candidate refinement blocks/work units: at most 250,000.

Caps are checked before allocation or input access whenever possible. A cap
failure is `CPU_SURVIVOR_PREREQUISITE_BLOCKED`, not a partial lane success.

## 10. Completion and kill criteria

### 10.1 Independent completion gates

`CPU_EXACT_PARTITION_CORE_VERIFIED` requires strict admission, finite
termination, canonicality under input permutation, response homogeneity,
all-action stability, quotient well-definedness, verified distinguishing words,
and agreement with the exhaustive independent solver.

`CPU_TIER_FIREWALL_VERIFIED` requires strict round trips, allowed conversions,
forbidden-conversion tests, representative-action and interval-undercoverage
kill fixtures, and no public promotion path from observed/nominal objects.

`CPU_HANKEL_PREDICTIVE_CORE_VERIFIED` requires immutable keyed data, a fitting
sentinel proving no target-cell read, complete training-footprint accounting,
exact rational reproduction on known low-rank fixtures, honest nonempty target
residuals, failure on adversarial mutation/incomplete shifts, permutation
canonicality, and terminal/nonterminal channel ablations.

`CPU_COMPONENTWISE_DIAGNOSTIC_VERIFIED` requires expand-then-contract,
good-versus-bad continuation, many-words-one-state, terminal nonmanufacture,
strict-decrease, censor/non-`NOT_APPLICABLE` oracle-field rejection, K+1
unresolved, transient-overshoot, ordering, and coordinate-length fixtures.

Each lane may instead close as `CPU_SURVIVOR_PREREQUISITE_BLOCKED` or
`CPU_SURVIVOR_LANE_FAILED` with the other lanes still reported honestly.
If the common admission lane fails, every lane is prerequisite-blocked. If
`WP4-E` fails, `WP6-T` is specifically `CPU_SURVIVOR_DEPENDENCY_BLOCKED`; this
does not decide `WP4-H` or `WP4-W`.

### 10.2 Bundle stop rule

Stop implementation and produce one consolidated closeout if any of the
following occurs:

- the amendment commit is not the exact green two-path child of `cc91a418...`;
- a result path, consumed artifact, or U05 input would change or be reopened;
- any implementation path falls outside the allowlist;
- the six-commit, per-lane commit quota, or enforced resource cap is exhausted;
- an incomplete/censored/boundary object would have to be serialized as exact;
- observed/nominal evidence would have to be promoted to hard/certified;
- fitting would need a target cell or the aggregate U05 artifact as a matrix;
- a protected/reserved task, excluded root file, LLM, GPU, SSH, native Lean,
  canonical RPC rerun, or new ledger subsystem would be needed; or
- hosted CI cannot be made green within the remaining budget.

No small amendment extends a blocked lane in this phase.

## 11. Mandatory nonclaims and later gates

This amendment does not license or claim:

- K1--K4, U'2--U'5, solve rate, ranking improvement, or a protected endpoint;
- a complete Lean reachable domain, all-germ Nerode quotient, contextual
  equivalence beyond the registered synthetic response vocabulary, M3 locality,
  or fiber completeness;
- a finite- or infinite-horizon envelope, Lyapunov/cocycle/pressure certificate,
  or positive weighted majorant;
- MaxEnt, KL calibration, predictive similarity, positive-safety similarity,
  global representation, or a true-target residual;
- a locality/CEGAR learner, occurrence-targeted `rw`, macro decomposition, or
  proposer performance;
- hard-tier inference merely because arithmetic is exact;
- generalization beyond the registered deterministic fixtures;
- reserved-data access, canonical RPC rerun, GPU/SSH work, deployment, or LLM
  proposer/distillation.

After this bundle, a separate `U'1.5-L` amendment is still required before any
locality learner or query matrix exists. A separate U'2--U'4 construction
amendment is required before envelope, MaxEnt, or similarity code. It must first
register a complete-fiber or independently certified finite-horizon upper
witness, then a hard envelope, then MaxEnt inside it, and then distinct
predictive/positive residual endpoints. GPU remains behind the filled
Amendment A.

## 12. Adversarial implementation-plan review

This document was attacked as an implementation plan, not as a second review
of the 2026-07-10 upper-stack theory verdict. Three independent lenses examined
the current code, frozen plan, result artifact, and CI/topology evidence:

1. `cpu_wp4_design`: exact-partition semantics, minimality, admission, finite
   feasibility, and synthetic-versus-Lean evidence;
2. `cpu_hankel_window_design`: predictor leakage, matrix completeness,
   trajectory denominators, transient expansion, and tier promotion; and
3. `cpu_governance_design`: red/green CI adjudication, immutable result
   topology, shallow-history repair, quarantine, authority, and anti-fractal
   limits.

Confirmed attacks and repairs:

| confirmed defect in a naive bundle | frozen repair |
|---|---|
| KP1 compression could be misread as a behavioral quotient result. | KP1 licenses drafting only; WP4-E uses independent synthetic complete systems and pairwise distinguishing-word verification. |
| The U05 depth boundary and aggregate artifact could be mistaken for exact chart/Hankel ground truth. | U05 data are provenance only; no reconstruction, promotion, or rerun is allowed. |
| Stability alone lets the identity partition masquerade as minimal. | Independent coarseness verification and shortest distinguishing words are mandatory. |
| Synthetic fixtures could fabricate Lean replay/cap/delta evidence and then shed provenance. | The nonerasable `synthetic_development` profile requires every Lean-only field to be `NOT_APPLICABLE`; all positive Lean/U05 adapters are absent. |
| `CLOSED` and `SINK` could merge when user response coordinates agree. | `totalized_kind` is an independent mandatory response-key component. |
| A predictor could select rank/pivots from target cells, alias the same response through another split, or omit rejected/shifted reads. | A capability-restricted training view, `ResponseAtomKey`, `r_train`, read sentinels, and the complete fit-time footprint are mandatory. |
| Exact rational arithmetic could be mislabeled hard evidence. | Hankel realization remains a development, nonpromotable type; hard operators require separate admission and completeness. |
| Seventy-four closing words could be reported as independent trajectories. | Occurrence and unique-state populations plus existential/universal continuations are reported separately. |
| Cycles make an unbounded universal-continuation claim undefined. | Frozen seeds, `D_start=4`, `K=4`, reverse `CanClose`, and all registered finite continuations define the quantifiers. |
| Endpoint contraction could hide intermediate expansion. | The exact positive-part overshoot formula and unresolved windows remain explicit. |
| A red result CI could be mistaken for a failed U05 probe. | The dated audited control-plane adjudication and green candidate run are frozen above. |
| Fixing CI inside the result commit would violate the four-path freeze. | The result stays immutable; the two-path successor amendment owns the guard correction. |
| Root LLM/task scratch files could leak into later inputs. | They are moved to a repository-external quarantine; LLM work is deferred behind exact generator and a later explicit amendment. |
| The bundle could regrow the evidence-ledger fractal. | One amendment, at most six semantic commits, one closeout, and no ledger/CAS/publication work. |

Final review disposition: **APPROVE for this exact two-path amendment and the
bounded WP4-E/WP4-H/WP4-W/WP6-T Windows-CPU implementation interval.** This is
not approval for protected evidence, Lean production integration, upper
operators, locality learning, similarity, GPU, or an LLM.
