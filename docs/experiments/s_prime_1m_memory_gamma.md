# S'1m Pre-Registration: memory-bearing Gamma chart on the rank-1 size mode

Status: TERMINATED BEFORE FREEZE (2026-07-07). Never executed; the
gate shot was never spent. See the termination record at the end of
this document. Retained as the registered record of why the licensed
memory-Gamma path closed.

## Question

S'1c measured: the reader's leakage is RANK-1 (96.9% = goal-size
motion variance) and has MOMENTUM (memory arm 36.1% vs reader arm
19.1% on linked pairs). Question: does a memory-bearing payment model
— the theory's R_tail = sum_k Gamma^k R with Gamma = one measured
scalar kernel on the size mode — recompute phi into a predictor that
passes the PRESERVED single-shot gate?

## License and scope (registered)

- This prereg spends the branch-(c) gate shot preserved by S'1c
  (instrument 5 never fired). The GATE FRAME is unchanged per S'1
  Amendment d: Amendment-a statistic, u definition, whitening,
  task-disjoint split, ||D|| race, corrected conjunct. What changes —
  and is the registered object under test, exactly as a reader
  extension would have been — is phi's payment model: the static cone
  becomes the tail-amplified cone below. The reader M_J itself is
  UNCHANGED.
- A memory win licensed ONLY this investigation (S'1c Amendment a);
  a FAIL here is terminal for middle-layer claims on this region:
  top-layer proposal, no further middle-layer prereg on this question.
- The loop-level memory module stays dead (E-MZ); this is a
  Gamma-chart payment correction, not a runtime memory cell.

## Frozen model

Size mode e1: the top leakage eigendirection from the S'1c published
spectrum (runs/s_prime_1c/leakage_spectrum.json), frozen as-is.

MEMORY KERNEL (lag-1 scalar, the only kernel the corpus can bear per
S'1c instrument 4's own scope note): on the 148 linked pairs, in the
co-moving estimation frame,

  (resp_t . e1) = alpha * (resp_{t-1} . e1) + b_{fiber(t)} + eps

with per-fiber intercepts at the frozen coarse classes (n_min = 8
shrinkage as in S'1c) and alpha global. Estimation: ridge-free least
squares; uncertainty by bootstrap over CHAINS (2,000 resamples).

TAIL-AMPLIFIED CONE: with tail factor tau = sum_{k=0}^{H} alpha^k,
H = 4 (the prior tail-horizon convention), every fit-side response row
r_i becomes

  r_i^mem = r_i + (tau - 1) * (r_i . e1) * e1

(non-size components untouched; e1 components amplified by tau).
phi_mem = dual-solve residual of the whitened task defect on the
r^mem cone (max_mass = None for phi_true, as registered).

## Gates (frozen order)

G0 PRECONDITION (does not spend the shot): alpha's bootstrap 95% CI
   excludes 0 AND its upper bound is <= 0.95 (contraction; the S'1
   Gamma discipline — no tail without a contraction certificate).
   If G0 fails: the kernel does not exist or is not contractive at
   lag 1; this prereg TERMINATES WITHOUT spending the gate shot, and
   the region passes to top-layer proposal with the license preserved
   fact recorded (a future corpus with longer chains may re-derive).
G1 MAIN GATE (spends the preserved shot; single execution): the
   Amendment-a corrected rule verbatim, with u_hat computed from
   phi_mem: task-disjoint walk-forward (fit pilot-era, score the ~103
   pilot-unseen train tasks), raced against ||D||; PASS requires
   rho_phi >= 0.10 with phi's own bootstrap CI excluding zero AND
   rho_phi - rho_baseline >= 0.10 with the difference CI excluding
   zero. Scale-ablation invariance (std/raw/log) required as in
   Amendment a. EVIDENTIAL DOWNGRADE carried over: the score side is
   the same reused 103 tasks; a PASS is provisional pending
   replication on unexposed waves.
   MANDATORY DIAGNOSTICS alongside (descriptive, non-gating): the
   walk-forward rho of (i) static-cone phi (the S'1 value, for
   delta attribution), (ii) the removed sweep component, (iii) tau
   and alpha with CIs.

## Litmus (before any real number; extends the certified stack)

Variant E in scripts/s_prime_1c_estimators.py: the synthetic generator
gains an AR(1) momentum term on the shared leakage mode
(eps1_t = alpha_true * eps1_{t-1} + innovation, alpha_true = 0.5);
the estimator must recover alpha within +-0.10 at the empirical
linked-pair count (n = 148, resampled chain lengths), and the
closed-form tail factor tau(alpha_true, H=4) within 10% relative
error. A no-memory variant (alpha_true = 0) must NOT pass G0 (CI
excludes 0 fails) in >= 90% of litmus replicates (false-positive
control for the precondition gate).

## Threats acknowledged in advance

- alpha is fit on 148 pairs from kernel-lane-biased chains; the
  momentum may be a property of the kernel-friendly tactic mix.
- e1 is frozen from the same corpus that fits alpha (shared-corpus
  reuse); the task-disjoint gate is the control, as always.
- H = 4 is a convention, not a fitted horizon; tau's sensitivity to
  H in [2, 8] is reported descriptively.
- A single global alpha ignores per-fiber kernel variation the corpus
  cannot support; disclosed.
- The score-side reuse downgrade (third look at the same 103 tasks)
  is inherited and disclosed; only unexposed-wave replication
  promotes a PASS.

## Termination record (2026-07-07): pre-freeze verification proved the
## gate unreachable; the draft is closed unexecuted

The pre-freeze adversarial verification (11 findings, 5 blockers)
established, by a COUNTERFACTUAL PROBE of the actual gate pipeline:

1. THE INTERVENTION CANNOT WORK. With max_mass = None the cone is
   invariant to per-generator scale; tau-amplification is a
   rank-rescale, not a re-ranking. Measured on the real gate: rho_phi
   moves from 0.070 to at most 0.083 over the ENTIRE G0-admissible
   alpha range (Spearman(u_hat_mem, u_hat_static) = 0.94-0.997). G1
   (rho >= 0.10, own CI excluding zero) is a foregone FAIL.
2. THE SIZE MODE IS NOT THE WHOLE BLIND SPOT. e1's 96.9% share is of
   gate-dims leakage only; carrier dims hold 57% of the total dedup
   trace — untouchable by any size-mode model.
3. FRAME/GRANULARITY MISMATCH. alpha lives on kernel-step co-moving
   residuals; the amplified object was file-lane attempt-level raw
   rows. Success rows have zero remaining tail; 84% of partial
   generators point ANTI-payment along e1 — the tail would have
   amplified anti-payment. e1 itself has no registered transport into
   the gate's 34-dim/alternate-whitening/log-mode frames.
4. CONFOUND: the licensing memory win (36.1%) was 5/6 prev-fiber
   onehot dims; the eig1-momentum dim's own margin was never
   decomposed — alpha may be tactic-sequence stickiness, not size
   momentum. The litmus variant as drafted was structurally blind to
   this confound.
5. GOVERNANCE: S'1 Amendment d's license-preservation text did not
   authorize this prereg to spend the preserved shot; the spending
   clause was drafted without authority.

DISCLOSED PEEK: the verification necessarily observed counterfactual
gate outcomes on the reused 103-task score side. Any future phi-model
redesign evaluated on this score side is a fourth look and carries no
evidential value. Consequence: the preserved gate shot is RETIRED FOR
THIS SCORE SIDE; any future middle-layer payability claim requires
fresh unexposed score data AND a fresh registration.

DISPOSITION: the licensed memory-Gamma path is CLOSED without
execution. The middle-layer question on this region passes to
TOP-LAYER PROPOSAL per the standing S'1/S'1c failure branches. What
survives as registered fact: the leakage geometry (rank-1 size motion
in gate dims + dominant carrier mass), a real but unconverted lag-1
memory structure, and the full metrology stack.
