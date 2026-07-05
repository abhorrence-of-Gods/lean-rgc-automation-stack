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

## Budget note

GPU: S3 ~$20-30, S4 arms (1)(2) ~$5, everything else CPU/local. The
vast.ai pod is a single point of failure: every rung archives off-pod
via the R0e collector before its analysis is trusted.
