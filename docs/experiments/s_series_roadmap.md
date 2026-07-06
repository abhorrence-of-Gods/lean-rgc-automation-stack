# S-series roadmap: stepwise corpus, distillation ladder, lemma foundry

Status: planning document (2026-07-05). Each rung gets its own frozen
preregistration before execution, per house style; thresholds here are
DRAFT until each rung's prereg is committed.

Strategic frame. G1 established that the RFT mechanism works (+13.1pt,
CI excluding zero, flaky-dominant). The free-energy theory (A0-A5) says
the next architectural decision — whether marginal GPU spend goes to the
middle layer (geometry: twist, spanner, factor bridge) or the top layer
(bigger/longer-trained LLM proposals) — is decided by the DISTILLATION
LADDER verdict (P4). Separately, kernel_rpc v2 (types/deps + prefix
replay, litmus-passed) makes a STEPWISE transition corpus cheap for the
first time, unblocking five gated measurements at once (M2, Q1-tactic,
Q3, Q5, E-Comm).

## Rungs

- S0 twist v2 consolidation (0 GPU, ~0.5 day). Promote the D1
  LogLiftModel into lean_rgc/grad/twist.py with the three unified heads
  (score_optimistic / state_value / score_post), trained on the 13,958
  audited rows now on disk (11,189 pilot + 2,769 G1 on-policy).
  Prerequisite for S4. No new science; unit tests only.

- S1 stepwise replay corpus (CPU+Lean, 1-2 days). Replay every verified
  script (116 RFT traces, G1 eval successes, 680 pilot successes) and
  every failed script's D3-verified prefix STEPWISE through kernel_rpc
  v2 (branch per tactic boundary), recording (S, A, E, S') with mvar
  graphs and state hashes per step. Deterministic, no LLM. Gate:
  >= 5,000 stepwise transitions with v2 payloads, archived off-pod.

- S2 M2 rider: proof-term minimal support (spawned session, Lean
  metaprogramming). After a successful tactic/script, extract the proof
  term, collect fvar dependencies, emit the minimal support set per
  goal. Litmus: a proof using one hypothesis among garbage reports
  exactly that hypothesis's closure. Unblocks the exact M1 rung and the
  full lemma foundry.
  LANDED 2026-07-05 (payload v3, litmus live on Lean 4.31: rfl after
  'intro a b h' -> ['b']; 'rw [h]' -> ['a','b','h'] via closure; plus
  used_constants, proof_hash_raw, and the alpha-invariant support_key).
  Granularity note from the parallel implementation: goals closed
  INSIDE a compound tactic block never surface in a goal list, so their
  closure attributes to the parent goal's support — the per-subgoal
  certificate requires tactic-step granularity, which is exactly what
  the S1 stepwise corpus provides. S1 therefore collects v3 payloads.

- S3 G1 seed replication + P1 gauge-tax arm (GPU, ~$20-30). Two more
  seeds of train(113)+paired-eval(130); registered amendment to the G1
  prereg. The P1 arm rides free: RFT trace dedup keyed at K0 (raw
  tactic) vs K1 (canonical) across seeds, comparing trace stats and a
  gradient-noise proxy. Gate: pooled CI across seeds still excludes
  zero.

- S4 distillation ladder, arms (1)(2) first (small GPU). Closed action
  space (premise actions + history top-k) on the 130-task eval set via
  the eval-mode driver: (1) frequency prior ranking vs (2) twist-v2
  ranking; success-per-FLOP curves. Arms (3) LLM-proposal-port and
  (4) full LLM follow only if (2) clears its preregistered floor.
  THE CENTRAL VERDICT: (2)~(4) => middle layer absorbs the next scale
  investment; (2)<<(4) => the soft residual is the asset and scale goes
  to P0; intermediate => the (3) hybrid becomes the default
  architecture.

- S5 Q-measurements on the S1 corpus (0 GPU). Q1-tactic (MI(t, t+k)
  decay after twist conditioning, tactic granularity), Q5 conditional
  correlation length, Q3 residual-MI spectrum if volume allows, and
  E-Comm order-swap statistics via kernel_rpc branch/rollback.

- S6 lemma foundry v0 (LLM+Lean, 1-2 days). For the 341 unique K1
  residual-goal keys from M1: conjecture auxiliary lemmas (pod LLM),
  verify through the bulk lane, and measure whether the M1 ladder's
  non-trivial inter-theorem hit rate moves off zero, plus a Delta(L)
  routing proxy. Full version (minimal-support canonicalized casting)
  once S2 lands.

- S7 geometry empirics (0 GPU). Mathlib dependency DAG via the premise
  index: detour-ratio distribution (spanner efficiency) and sampled
  Gromov delta (hyperbolicity); toy1-reduced re-scoped as the exact
  ELBO-gap protocol backing S4's metric.

## Dependencies

S0 -> S4. S1 -> S5 and the exact rungs of S6. S2 -> S6-full and
M1-exact. S3 independent (protects the G1 claim). S7 independent.

## Explicitly deferred (unchanged verdicts)

Renderer/G3 (behind the 4th-arm result), memory module (killed by
E-MZ), BP/junction-tree (behind toy1/S7 exactness evidence), model
scale-up (behind the S4 verdict — the ladder decides WHERE scale goes).

## Revision 2 (2026-07-06): post-G1re3, response-algebra re-centering

Context. G1re3 (first label-sound execution) landed the pre-declared
"<+2pt" branch: RFT-primary is unsupported at 7B under this budget
(honest baseline ~5%, 5 verified traces per 8 waves). The registered
consequence — marginal GPU pivots to the search side, gradient becomes
the LAST resource (an internalization event, not a stream) — coincides
with the response-algebra re-centering: the middle layer (response
matrix, coker, Gamma, quotient, twist) learns densely from FAILURES and
is the natural cold-start object. Three ledgers govern everything:
hard (verifier-adjudicated), soft (calibration; failures update it),
asset (verified AND walk-forward-valued).

Frozen corrections adopted with the re-centering:
(a) Response rows of mislabeled audits carry FABRICATED after-states
    (synthetic closed state on false success) — the middle layer is
    rebuilt from re-audited rows, not by flipping labels.
(b) Coker residuals have a 4th false-positive source: the budget
    constraint |j|_1 <= M; phi must be split into budget-bound vs
    truly-unpayable by re-solving with relaxed M.
(c) E1 citations are decontaminated: raw-text conditioning is a prior,
    not a result (E1 withdrawn under authoritative labels).
(d) Dense signals (defect deltas, prefix length) NEVER enter the reward
    channel — hard reward stays 0/1 adjudication; density lives in
    baselines, curriculum keys and soft calibration. Even
    verifier-anchored prefix length is gameable.
(e) Failure-side metrology: isolation confirmation covers successes
    only; every run adds a random FAILURE spot-check (n>=20 isolated
    re-audits) to bound the residual false-failure (conservative) bias.

Rungs (S' series; supersedes ordering above where in conflict):

- S'0 Level 0 — definitive corpus re-audit (pod, overnight, CPU).
  Isolated (batch=1) re-audit of ALL pilot + G1-era rows (~18k),
  producing sound labels AND sound response vectors in one pass.
  Everything middle-layer depends on this.
- S'1 Levels 5-6 — middle-layer rebuild + coker go/no-go (0 GPU).
  Rebuild R_J / carrier matrix / Gamma (post pred_response fix) /
  response quotient on S'0 output. REGISTERED GATE: does phi (split per
  (b)) predict FUTURE walk-forward defect reduction? If not, extend the
  reader (M_J) before any foundry use. Includes S1-driver OOM fix and
  the stepwise corpus rerun (S5 measurements ride on it).
- S'2 Levels 1-3 — training redesign prereg (G1c), gated on S'1.
  Curriculum from residual goals (D3 verified prefixes as easier
  subtasks) + valid-split tasks + qgen, targeting per-task p in the
  information band [0.2, 0.5]; twist state_value allocates samples;
  dense signals per (d). LAUNCH GATE: projected verified-trace supply
  >= 20/wave, else training stays shelved.
- S'3 Level 4 — search-side pivot (where marginal GPU goes now).
  Twist rerank-only in the eval harness, D3 gated suffix-repair and
  continuation arms (their gates were position-based and survive the
  label corrections), SMC-shaped scheduling; the S4 ladder arms (1)(2)
  re-scoped onto sound labels as the measurement.
- S'4 Levels 7-8 — coker-conditioned foundry (S6 prereg amended per
  (b)/(c)): proposal bundles = raw exemplars where phi_true is strong;
  asset-type and generalization-level selection as reported columns;
  acquisition model stays one-level log-linear.
- S'5 Level 9 — internalization as model-release events. Condition:
  discounted external-reference cost exceeds one-shot internalization
  cost. Currently trivially unmet (assets tiny); explicitly deferred.
- S'6 Level 10 — standing metrology: isolation confirmation +
  canaries + reproducibility (structural since 2026-07-06), plus (e)
  failure spot-checks; audit means are chosen by value-of-information.

## Budget note

GPU: S3 ~$20-30, S4 arms (1)(2) ~$5, everything else CPU/local. The
vast.ai pod is a single point of failure: every rung archives off-pod
via the R0e collector before its analysis is trusted.
[Rev 3: S3 budget line void; see below.]

## Revision 3 (2026-07-06): adversarial-review corrections

Context. A full adversarial review of this roadmap plus the
response-algebra re-centering (30 findings surviving refutation, 7
critical; verified against repo code, on-disk artifacts, and the
registered record) found that Revision 2's supersession clause covered
ordering only, leaving dead-premise text executable with budget
attached, and that several registered gates were unmeasurable or
gameable as written. This revision fixes supersession semantics,
strikes dead text, re-registers those gates, and records S'0 execution
facts.

### Supersession semantics (replaces the Rev 2 clause)

Revisions 2 and 3 supersede PREMISES, not just ordering. Any earlier
text conflicting with the G1re3 registered record or corrections
(a)-(e) is void. The S0-S7 list is retained as history; no rung from it
may execute except under a fresh prereg that cites this revision.

### Struck text

- Strategic frame (top of file): the "+13.1pt, CI excluding zero"
  sentence is VOID. Authoritative record: G1 invalidated (g1 amendment
  c); corrected recount +3.85pt CI [-0.77,+8.46] not excluding zero;
  authoritative isolated recount -0.77pt; label-sound G1re3 +1.54pt CI
  [+0.00,+3.85], NOT SUPPORTED.
- S3 is KILLED, not deferred: its gate presupposes a retracted
  exclusion and its execution ("more waves of the same") violates the
  registered <+2pt branch. Its $20-30 GPU line is freed toward S'3. The
  P1 gauge-tax rider is explicitly deferred; it may only be re-homed
  inside a future fresh training registration (G1c or later).
- S0 as written is VOID. The on-disk runs/s0_twist_v2/twist.json is the
  quarantined pre-fix artifact (base_rate back-solves exactly to
  823/13,957 uncorrected labels; built 94 min before classifier fix
  a681bd1); a QUARANTINE.md marker now sits beside it. Twist rebuild is
  re-specified under S'1b below.
- S1's ">= 5,000 stepwise transitions" gate is VOID: the built
  inventory ceiling is 1,941 expected transitions (1,102 deduped
  scripts, median 1 step), shrinking further under sound labels. The
  S'1 prereg re-registers the gate from the S'0-verdict-filtered
  inventory; the S5 volume hedge extends from Q3 to Q1/Q5.
- S6's 341 K1 keys AND its frozen walk-forward goal set are pre-fix
  artifacts. Both must be re-derived from S'0 output, and the S6 prereg
  amendment (per (b)/(c) AND this clause) must exist as a dated section
  in s6_lemma_foundry.md before S'4 executes.

### S'0 — execution record and additions

Execution record (2026-07-06): dedup at (task_id, script) yields 4,912
unique pairs (pilot 2,517 / g1_train 1,624 / g1_evalC 519 / g1_evalT
252); manifest archived off-pod at runs/s0_reaudit_input_pairs.jsonl.
Isolated batch=1 re-audit via the bulk lane, 4 shards, timeout 300 s,
launched on the pod; task-def join verified lossless (0 dropped pairs)
while the shards ran. Note: at batch_size=1 the bulk lane never writes
isolation_confirmed (bulk_executor.py:246) — verdict provenance is
"isolated by construction (batch=1)"; consumers key on the verdict
files, not the flag.

Additions frozen with this revision:
(f) ADJUDICATOR ACCEPTANCE — "authoritative" does not attach to S'0
    labels until the fixed classifier itself passes a registered
    acceptance test: a stratified golden sample (n >= 60; strata: src x
    verdict x error-class) re-verified through the single-audit lane
    plus manual inspection, and a seeded fault-injection smoke (known
    true-positive and true-negative scripts). Any classification error
    stops the label release. (The only prior ground-truthing on record
    was a 5-sample check during defect discovery.)
(g) S'0 delivers sound LABELS only. Failure-side response vectors
    remain synthetic (error-message after-states, bulk_executor.py:318;
    the extractor quadruple-counts message text). Sound failure-side
    response vectors require parsing genuine residual goals out of the
    stored messages (LeanMessageParser; recoverable for the ~64% of
    failures with status=partial) — scheduled inside S'1, and the
    "sound response vectors in one pass" claim in S'0's rung text is
    corrected accordingly.
(h) Correction (e) re-sized: n >= 20 is a gross-regression tripwire,
    not a bound (0/20 clean bounds false-failure only below ~13.9% at
    95%). Standing instrument: either derive n from a registered target
    bound (e.g. 2% -> n ~ 150) or label the check "tripwire only" in
    every report that cites it.
(i) Corpus manifest replaces "~18k": locally verifiable rows 15,576
    (11,189 pilot tarball + 2,769 g1_prod_train + 859 g1_eval_C + 759
    g1_eval_T) plus the G1re3 eval-arm wave rows now archived off-pod
    (runs/g1re3_eval_{C,T}/wave_rows_archive.tar.gz, 2,014 wave rows;
    pulled and count-verified 2026-07-06).

### S'1 — gate re-registration (frozen into the S'1 prereg)

- WALK-FORWARD DEFINED TASK-DISJOINT: fit R_J/phi on pilot-era rows;
  score phi's predictive value ONLY on G1-era wave rows restricted to
  train tasks unseen in pilot data. Eval-side temporal slices are
  barred (pilot rows cover 124/130 eval tasks; a phi that fingerprints
  tasks would pass any time-only split).
- UNITS PINNED before any phi is read: a registered per-dimension
  weighting (revive DefectWeights or z-score frozen from S'0 output).
  The defect vector currently mixes raw counts, log1p scales and 0/1
  flags in one unwhitened L2 (DefectWeights is dead code); phi's
  direction, j's support, and the (b) split all flip under rescaling.
  A scale-ablation control is registered alongside the reader-extension
  (M_J) no-go branch, so a gate failure is attributable.
- Correction (b) implemented as a dual solve: default max_mass vs
  max_mass=None (coker.py already accepts None); residual components
  labeled budget-bound vs truly-unpayable.
- BASELINE RACE: phi's prediction must beat scalar ||D|| difficulty
  (house "race the raw signal" norm, d1_twist_gate.md), not merely
  correlate.
- DEGENERACY HARD-FAIL: any rebuilt transition set containing
  pred_response_source='realized_fallback_degenerate' rows fails the
  rebuild; the try/except-pass swallow around response-model training
  is removed on this path. Gamma acceptance adds per-action holdout and
  a contraction gate on live tail paths (actions with rho >= 1 are
  excluded from tail scoring or clipped; the clip-guarded helper is
  currently dead code while live paths are unguarded).
- QUOTIENT NAMED AND GATED: the prereg names which implementation is
  rebuilt (contextual_congruence registry vs quotient.py union-find —
  currently two disconnected implementations share the name) and
  registers a held-out acceptance criterion; bootstrap_stability is
  populated or the field is removed.
- MODEL-ERROR CONTROL: a registered test separating linear-payability
  model error from reader blindness (via the S1 stepwise corpus: does
  phi ~= 0 imply some action SEQUENCE pays?), so NO-GO branches are
  attributable to the right cause.

### S'1b — twist rebuild (replaces S0)

Twist v2 is rebuilt on S'0 re-audited labels with an EVAL-TASK-DISJOINT
row selection; runs/g1re3_train (7,017 rows, 114 train tasks, verified
zero eval overlap) suffices as the clean base. Any eval-facing use of a
twist fit on eval-task rows is barred — the same rule g1's prereg
applied to model weights (g1:9-12) now explicitly covers middle-layer
artifacts.

### S'2 — additions

- LAUNCH GATE RE-BASED: the unspecified "projection" is replaced by a
  measured, registered canary wave on the frozen curriculum, counting
  isolation-confirmed traces on non-eval-derived, non-degenerate tasks.
  (Honest observed supply is 0.625 traces/wave; the 20/wave bar stands.)
- CURRICULUM TASK-EXCLUSION: mirrors g1's contamination rules. The
  current D3 prefix pool is 100% eval-task and must be rebuilt from
  train-split failures; qgen conditioning must exclude eval-task rows.
- BASELINE ADMISSIBILITY (closes a loophole in correction (d)):
  baselines in any policy-gradient update must be action- and
  trajectory-independent given the state (e.g. group mean of hard
  reward). Trajectory-derived dense baselines (defect deltas, prefix
  length) bias E[grad log pi * (R - b)] — dense reward shaping by
  another name — and at ~5% base rates would supply ~100% of the
  gradient in all-fail groups. Barred from the reward channel's
  gradient path entirely.

### S'3 / S4 — additions

- Twist in any eval-facing arm must be the S'1b eval-disjoint artifact.
- The success-per-FLOP accounting convention (what enters the
  denominator per arm: Lean CPU, twist inference, LLM forwards) must be
  defined in the S4 prereg BEFORE arms run — the verdict can flip on
  the convention alone, and "FLOP" is currently defined nowhere.
- POWERING: at the honest ~5% base rate, 130 tasks yields single-digit
  successes per arm and the three-way verdict bands are simultaneously
  consistent with one CI. The S4 prereg must either enlarge the eval
  set (reserving the valid split for eval takes precedence over S'2
  consuming it as curriculum) or move the primary endpoint to dense
  per-step verifier-adjudicated events.
- D3 licenses are RE-RUN, not asserted: the "position-based gates
  survive" parenthetical is replaced by a G0b coverage recomputation on
  corrected labels (the pool is label-defined; the corrected pool
  likely fails G0b at 95%, making outcome gates unreadable until
  re-established).

### S'4 — additions

- Frontier (341 keys) and the walk-forward goal set re-derived from
  S'0 output (see Struck text).
- The hit-count GO gate gains a permutation/decoy-lemma null and gates
  on excess over the null (a rate, not an absolute count).
- Asset-ledger promotion requires a registered minimum per-asset
  evaluation n or selection-corrected Delta_wf (winner's-curse control).
- A_theta remains a REPORTED COLUMN; any transition to live proposal
  reweighting (exp(A/tau)) requires its own prereg.

### Governance

The three ledgers get an owning artifact (schema + file) before S'1
reads or writes them. Clarification resolving a latent contradiction:
middle-layer rebuilds consume failure rows as SOFT-ledger content;
asset-ledger exclusivity governs ACTION-UNIVERSE EXTENSION only, not
statistical recalibration of the middle layer.

### Off-pod status

g1re3_eval_{C,T} wave-row archives pulled off-pod and count-verified
2026-07-06 (31 jsonl files, 4,180 + 4,166 rows; the 2,014 wave rows
match pod-side counts). S'0 verdict shards must be pulled off-pod
before any label release or analysis.

### S'0 execution result (2026-07-06, same day)

The 4-shard isolated re-audit COMPLETED (4,912 pairs, 1,228/shard,
~2.8h/shard; verdicts + per-shard micro_audit archived off-pod at
runs/s0_reaudit/). Acceptance per (f):
- Reproducibility: 394/394 agreement with the 2026-07-05 authoritative
  isolated re-audit (0 status flips).
- Cross-lane: 82-item stratified golden sample re-verified through the
  independent single-audit lane, 82/82 agreement.
- Manual inspection of all 35 surviving successes CAUGHT DEFECT #6:
  6 were the bare script `sorry` (both lanes classified exit-code-0 +
  "declaration uses 'sorry'" warning as success; cross-lane agreement
  was blind to it because the lanes share the classifier). Registered
  as g1_preregistration.md amendment g; classifier fixed in both lanes
  (executor._classify_success; bulk _errors_by_line collects sorry
  warnings); regression test tests/test_v100_sorry_success_hole.py.
- Corrected release: 29 true success pairs (pilot 27 / g1_train 1 /
  g1_evalC 1 / g1_evalT 0); G1re3 corrected to 2 verified traces and
  C=5/130, T=7/130 with the paired delta and NOT SUPPORTED verdict
  unchanged (the demoted task was concordant). Labels:
  runs/s0_reaudit/corrected_labels.jsonl; demotion evidence:
  runs/s0_reaudit/defect6_demotions.json. Failure-status churn is
  large (elab_error<->fail ~1.8k rows), confirming (g): failure-side
  response vectors need the message-parse amendment before S'1 trusts
  them.
- Top-up (same day): 228 unique pilot pairs were absent from the
  original manifest (157 non-ASCII scripts dropped at extraction, 71
  other); re-audited with the FIXED classifier (4 shards, ~8 min):
  0 successes, 1 sorry-holed script correctly classified unsafe in
  production. Pilot store coverage is now 11,189/11,189 rows; total
  corpus 5,140 verdict pairs across 8 shards. Final release stands at
  29 true success pairs.
- S'1 prereg drafted for freeze: docs/experiments/
  s_prime_1_middle_layer.md (gate, units, attribution ladder, and the
  re-registered stepwise transition gate >= 1,141 of the measured
  1,427 ceiling).
