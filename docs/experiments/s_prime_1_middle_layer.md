# S'1 Pre-Registration: middle-layer rebuild + coker go/no-go

Status: DRAFT for freeze (2026-07-06). Written against roadmap Revision
3's frozen gate re-registration; the single [FREEZE] placeholder is
computed and filled at commit time. Amendments after freeze require a
new dated section with a reason.

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
