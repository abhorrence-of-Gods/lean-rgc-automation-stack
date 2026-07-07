# S'1 Pre-Registration: middle-layer rebuild + coker go/no-go

Status: FROZEN 2026-07-06, before execution. All thresholds below are
registered; amendments require a new dated section with a reason.

## Question

Does the coker residual phi, computed from label-sound response rows,
predict which defect directions the existing action universe will FAIL
to pay in future waves — i.e., is the middle layer a real geometry
worth re-centering on, or an artifact of reader blindness, unit
scaling, or linear-payability model error? This is the go/no-go for
S'2 (training redesign) and all foundry use of phi (S'4).

## Inputs (frozen)

- Labels: runs/s0_reaudit/corrected_labels.jsonl + defect-#6 demotions
  (adjudicator acceptance passed 2026-07-06: 394/394 reproducibility,
  82/82 cross-lane, manual inspection; g1 amendment g).
- Response rows are REBUILT, not reused. Failure-side after-states are
  re-derived by parsing genuine residual goals from stored messages
  (LeanMessageParser lane) for status=partial rows; rows whose
  after-state cannot be recovered carry after_state_source='synthetic'
  and are EXCLUDED from R_J/Gamma/quotient fits (retained for label
  statistics only). This implements Rev 3 correction (g); the
  bulk-lane error-text pseudo-states measured in the review (e.g.
  num_goals=4.0 on a single-goal state) must not enter any chart.
- Row stores (all off-pod verified): pilot tarball, g1_prod_train,
  g1_eval_C/T, g1re3_train, g1re3_eval_C/T.

## Units (frozen BEFORE any phi is read)

- Whitening: per-dimension z-scoring with mean/std frozen from the
  corrected pilot-era fit population; near-constant dims (std < 1e-6)
  get weight 0. The dead DefectWeights mechanism is revived as the
  carrier of these weights, applied at projection time.
- Scale-ablation control: the full gate analysis is re-run under (i)
  raw units and (ii) log-only scaling. If the gate verdict is not
  invariant across the three weightings, the verdict is UNSTABLE-UNITS
  and no other branch (including extend-M_J) may be taken until the
  reader's scale is fixed.

## Rebuild list (frozen)

1. R_J response table (per-action + per-class charts) on sound rows.
2. Carrier matrix (same row filter).
3. Gamma transitions, post pred_response fix, with DEGENERACY
   HARD-FAIL: any transition batch containing
   pred_response_source='realized_fallback_degenerate' aborts the
   rebuild (the try/except-pass swallow is removed on this path).
   Per-action acceptance: holdout rows never enter per-action fits;
   contraction gate: actions whose live diag chart has rho >= 1 are
   excluded from tail scoring (H-truncated report allowed, flagged).
4. Response quotient: the contextual-congruence registry lane is the
   ONE implementation rebuilt (quotient.py's union-find lane is out of
   scope for S'1). Held-out acceptance: per action, rows are hash-split
   50/50; fingerprints fit on half A; a congruence class is ACCEPTED
   only if its held-out within-class cosine >= 0.95 and the same merge
   decision recurs when fit on half B; failing classes dissolve to
   singletons. bootstrap_stability is populated or the field removed.

## phi computation (frozen)

- Dual solve per Rev 2 correction (b): project at max_mass=1.0 AND
  max_mass=None. phi_true = residual at M=None (truly-unpayable);
  phi_budget = phi(M=1) - phi_true (budget-bound). Only phi_true feeds
  the gate and any downstream foundry conditioning.
- Disclosure: ridge=1e-4 shrinks j and inflates phi; reported, not
  corrected, in v0.

## THE REGISTERED GATE (task-disjoint walk-forward)

- FIT side: pilot-era rows (2026-07-03/04). SCORE side: G1-era wave
  rows (g1_prod_train + g1re3_train) restricted to train tasks with
  ZERO pilot rows (verified 0/130-eval overlap; ~103 tasks). Eval-side
  or time-only splits are BARRED (pilot covers 124/130 eval tasks; a
  task-fingerprinting phi would pass them).
- Primary statistic: per score-side task, predicted unpaid fraction
  u_hat = ||phi_true(D_task)|| / ||D_task|| (whitened norms, charts
  from FIT side only) vs realized unpaid fraction u = whitened defect
  norm remaining at the task's last G1-era wave over its initial norm.
  Spearman rho(u_hat, u) with BCa bootstrap CI over tasks.
- BASELINE RACE (house norm, d1): the same statistic for the scalar
  difficulty predictor ||D_task|| alone. PASS requires
  rho_phi - rho_baseline >= 0.10 with bootstrap 95% CI of the
  difference excluding zero. Correlation without beating the raw
  signal is a FAIL.

## NO-GO attribution ladder (frozen order)

(a) UNITS: verdict not invariant across weightings -> UNSTABLE-UNITS;
    fix reader scaling; no other branch may fire.
(b) MODEL ERROR control: on the S1 stepwise corpus (rerun inside this
    rung), measure the sequential-payment fraction: of stepwise-closed
    goals, how many have NO single action in the universe paying their
    initial defect while the observed SEQUENCE pays it. If > 30%, the
    binding error is linear payability (one-shot additive cone), and
    the remedy is sequential/Gamma-composed charts — extend-M_J is
    barred as a diagnosis.
(c) READER BLINDNESS: only if (a) and (b) pass and the gate fails may
    the extend-M_J branch fire (raw-text/identifier features), per
    theory section 10; a second failure after extension returns the
    region to top-layer proposal.

## Riders (frozen scope)

- S1-driver OOM fix: driver-level worker recycle with a bounded-memory
  acceptance test and an incident note; no Lean-side rework in S'1.
- Stepwise corpus rerun on corrected labels; the void ">= 5,000
  transitions" gate is re-registered against the verdict-filtered
  inventory ceiling, computed 2026-07-06: 28/394 success scripts
  survive the corrected labels (31 transitions) + 708 D3 verified
  prefixes (1,396 transitions) = 1,427 expected transitions. GATE: the
  rerun yields >= 1,141 v3-payload transitions (80% of ceiling; the
  slack absorbs replay breakage). Note: stepwise replay re-verifies
  every step through kernel_rpc, so prefix soundness is re-established
  at replay time regardless of the pending D3 G0b re-run, which
  affects D3's OUTCOME gates only. S5 volume hedge extends from Q3 to
  Q1/Q5.
- No GPU. All analysis on off-pod stores; any pod artifact is pulled
  and count-verified before it is read.

## Threats acknowledged in advance

- Score-side rows are on-policy for a different sampler and carry the
  AWQ->NF4 protocol change; accepted and disclosed.
- Per-task granularity conflates state-level payability; a state-level
  gate needs the stepwise corpus and is deferred to the rerun.
- ~103 score-side tasks bound the Spearman power; the gate races
  effect size, not significance alone.
- g1_prod_train generation policy was corrupted-era; labels are
  corrected but the row distribution is biased toward that policy's
  proposals.

## Amendment a (2026-07-06): signed-race gate defect; corrected verdict

Reason: first execution of the registered gate exposed a specification
defect. The race statistic rho_phi - rho_baseline is SIGNED, and the
baseline turned out strongly ANTI-correlated with the outcome
(rho_base ~= -0.52: larger initial defects show larger fractional
partial progress, plausibly because token-count dims are the most
reducible), so the difference clears +0.10 while phi itself predicts
nothing. Formal registered result, recorded: PASS in all three
weightings (std/raw/log; diff +0.59/+0.54/+0.54, CIs excluding zero;
n=103 tasks, 1,394 fit rows; runs/s_prime_1/gate_report.json).

Corrected gate (registered by this amendment, applied prospectively
and to this execution): PASS additionally requires rho_phi >= 0.10
with phi's OWN bootstrap 95% CI excluding zero. Measured: rho_phi =
+0.07 (std), +0.07 (raw), +0.015 (log); own CI [-0.14, +0.28] includes
zero. CORRECTED VERDICT: FAIL, invariant across weightings.

Attribution ladder status:
(a) UNITS: cleared — the (corrected) verdict is invariant across all
    three weightings; the failure is not a scaling artifact.
(b) MODEL ERROR: NEXT — the sequential-payment fraction on the S1
    stepwise corpus (rerun on corrected labels, 736-script inventory,
    gate >= 1,141 transitions) decides whether the one-shot additive
    cone is the binding error before extend-M_J may fire.
(c) READER BLINDNESS: barred until (b) completes.

Interim consequence (per Rev 3 and the frozen prereg): phi does not
certify as a foundry conditioning signal; S'4's phi_true-conditioned
proposal bundles remain BLOCKED on this gate. The S'2 launch gate is
unaffected (it never depended on phi passing — training stays shelved
on supply grounds regardless).

## Amendment b (2026-07-06): rider corrections registered BEFORE the
## stepwise rerun launch (pre-launch adversarial verification findings)

Reason: a pre-launch adversarial verification of the recycled driver
and rider design found one blocker and three majors; all are corrected
here before any pod time is spent.

1. BRANCH (b) THRESHOLD UNREACHABLE (blocker). The registered >30%
   sequential-payment fraction has an arithmetic ceiling of 3/28 =
   10.7%: the honest success-side inventory is 25 one-step + 3
   two-step scripts (the corrected corpus simply contains no deep
   verified proofs at 7B supply). The original fraction is
   RE-REGISTERED AS DESCRIPTIVE ONLY. The BINDING instrument for
   linear-payability model error becomes the ADDITIVITY TEST, which
   the same planned corpus powers at n~700:
   - Realized payment per chain: P = defect(S_0) - defect(S_last), at
     kernel-goal granularity (extractor run on kernel-provided goal
     text; NO message text), both sources, partial payment included
     for d3 chains.
   - Predicted payment: P_hat = sum_k Rbar(tactic_k), where Rbar is
     the corpus-wide mean step response of the normalized tactic —
     exactly the cone's state-marginalized additive assumption.
     Tactics with < 3 occurrences are excluded; chains with < 80% step
     coverage are skipped (coverage reported).
   - REGISTERED RULE: linear payability is BINDING if the median
     relative error ||P - P_hat|| / max(||P||, 1e-6) over covered
     chains exceeds 0.50. Secondary descriptive: per-tactic response
     dispersion (1 - R^2 vs the global mean) for tactics with >= 5
     occurrences.
2. STRICT GATE CURRENCY (major). Failure payloads clone the
   before-state, so "v3-payload transitions" is redefined: status in
   {success, partial} AND kernel_state_after non-null AND kernel
   schema v3. The driver now reports v3_success_transitions; the gate
   reads THIS counter.
3. DEFECT #6 RECURRENCE GUARD (major). The kernel_rpc lane has no
   sorryAx detection (sorry CLOSES goals there); Lean-side detection
   is out of S'1 scope. Mitigations: 3 bare-sorry d3 prefixes dropped
   from the inventory, and the driver refuses to execute any script
   whose steps contain sorry/admit (skipped_unsafe, chain recorded
   broken).
4. INVENTORY RE-FROZEN: +1 recovered true-success pair
   (mathd_numbertheory_85, norm_num — a false-failure recovered by
   S'0, absent from the pre-fix inventory), -3 sorry prefixes:
   734 scripts, 1,424 expected transitions. GATE: >= 1,139 strict
   v3 transitions (80%).
5. BREAKAGE-ADJUSTED VOLUME RULE (major). 4 long d3 chains
   (39/75/90/170 steps) hold 374 expected transitions (26% of
   ceiling), so honest replay breakage can fail the volume gate alone.
   chains.jsonl records n_steps vs completed_steps, making the
   break-attributable shortfall exact. RULE: if the strict count is
   below gate but >= 80% of the shortfall is attributable to chain
   breaks concentrated in <= 5 identified scripts, rung (b) PROCEEDS
   on the achieved corpus with a disclosed volume note; otherwise the
   broken chains are re-attempted (larger --timeout-s) before any
   verdict is read.
6. Durability/join hardening (recorded): per-chunk flush (no chunk's
   work is lost on a later startup failure), chain records carry
   script_index (the analysis join no longer assumes enumeration
   alignment), and a missing kernel goal count counts as NOT closed.

## Amendment c (2026-07-06): stepwise rerun executed; branch (b) verdict
## NOT-BINDING (razor-edge); D3 pool empirically collapses; lane
## divergence disclosed

Execution record. Rerun 1 (recycle_every=40) OOM-killed its worker in
every chunk (~14 Environments exhaust the container cgroup; exit 137;
archived runs/s_prime_1/rerun1_summary_oom137.json). Rerun 2
(recycle_every=8): 734 scripts, 91 recycles, 2.75 h, register_failed
18 (9 statement-parse, 9 residual), 692 strict v3 transitions.

1. VOLUME GATE: FAIL (692 < 1,139) — and the gate is declared
   UNSATISFIABLE AS FROZEN: 187 of the 200 broken chains are
   corrupt-era D3 prefixes rejected at step 0 (170 were never
   re-audited pairs — their only "verification" was the corrupt-era
   probe — and 17 are S'0-adjudicated fail). The 1,424-transition
   ceiling was therefore built on the un-re-derived D3 pool; the
   adversarial review's D3 finding is now EMPIRICALLY CONFIRMED by
   kernel replay. Consequence: S'3's D3 arms stay blocked pending pool
   re-derivation from S'0 output; the corpus gate is re-based to the
   achieved sound corpus.
2. LANE DIVERGENCE (new standing threat): 13/29 (45%) of file-lane
   TRUE successes fail at kernel step 0 (ring/linarith/simp on
   numeral goals), and of 16 success chains completing all steps only
   2 CLOSE in kernel semantics. The kernel corpus under-accepts
   relative to the adjudication lane: every kernel-corpus measurement
   (S5, E-Comm) carries tactic-selection bias, and cross-lane label
   transfer is barred without a divergence study.
3. BRANCH (b) VERDICT — additivity test (Amendment b instrument):
   n=163 covered chains (381 skipped below 80% tactic coverage; 39
   tactics hold a global mean), median relative error 0.4956,
   bootstrap CI95 [0.406, 0.545], P(median > 0.50) = 0.148.
   NOT-BINDING per the frozen 0.50 rule; the razor-edge margin and the
   straddling CI are disclosed. Secondary (descriptive): per-tactic
   response dispersion is severe exactly for the payment-relevant
   closers (1-R^2: congr 0.94, norm_num 0.88, ring 0.76) — the
   state-marginalized chart is marginal even where not formally
   binding. Descriptive sequential fraction: 0/2 (kernel closure
   semantics shrank the denominator; ceiling already disclosed).
4. LADDER STATE: (a) units cleared; (b) not binding => branch (c) MAY
   fire: ONE reader extension (raw-text/identifier features in M_J)
   followed by a single phi-gate re-run under the Amendment-a
   corrected rule; a second failure returns the region to top-layer
   proposal per theory section 10.

## Amendment d (2026-07-07): branch-(c) license extended to the S'1c
## pipeline; gate frame pinned; branch-(b) reopening registered

Reason: branch (c) is executed under the S'1c prereg
(docs/experiments/s_prime_1c_reader_extension.md), whose v1 draft
failed pre-freeze adversarial verification (18 findings, 6 blockers);
v2 embeds the fixes. This amendment registers the three points that
touch THIS document's frozen ladder:
1. GATE FRAME PINNED: the single licensed phi-gate re-run fires in the
   Amendment-a frame exactly (raw whitened norms, task-disjoint,
   ||D|| race, corrected conjunct). The S'1c sweeping/co-moving frame
   is estimation-side only and never gate-bearing — a gate-substrate
   change is not licensed by branch (c).
2. LICENSE PRESERVATION RULE: the one gate shot is spent only when
   S'1c instrument 5 actually fires. If the capacity-bounded Schur
   criterion is not met, no extension is tested, the license is
   preserved, and the leakage spectrum is still published.
3. BRANCH-(b) REOPENING: S'1c instrument 4 (equal-capacity memory
   race on the 148 linked pairs, verdict-bearing only at n >= 120) is
   a registered reopening of the sequential-structure question under a
   new same-corpus instrument, superseding the Amendment-b additivity
   rule for this purpose only. It is also registered as the re-test
   required by emz_memory.md's resurrection clause (reader coordinates
   changed: kernel-granularity chart); a memory win licenses only a
   Gamma-chart-memory investigation under a fresh prereg, not the
   killed loop-level memory module.

## Amendment e (2026-07-07): middle-layer closure on this region

The licensed memory-Gamma prereg (S'1m) was TERMINATED BEFORE FREEZE:
its pre-freeze verification proved by counterfactual probe that the
tau-amplified cone cannot reach the gate threshold at any admissible
alpha (rho_phi max 0.083 vs required 0.10, rank-rescale not
re-ranking), and that the verification itself constituted a peek at
counterfactual gate outcomes on the reused score side. The preserved
branch-(c) gate shot is RETIRED FOR THIS SCORE SIDE. The ladder's
terminal state: (a) units cleared, (b) additivity not binding at the
razor edge / memory real but unconvertible, (c) reader extension
Schur-blocked at 10.6% — ALL registered middle-layer paths on this
region are now closed, and the region passes to TOP-LAYER PROPOSAL.
Surviving registered facts: the corrected corpus and metrology stack
(S'0, defect #6, golden protocol), the leakage spectrum
(runs/s_prime_1c/leakage_spectrum.json) as top-layer design evidence,
and the S'3 search-side items that never depended on phi (twist
rerank with the eval-disjoint S'1b artifact; D3 pool re-derivation).
Any future middle-layer payability claim requires fresh unexposed
score data and a fresh registration.
