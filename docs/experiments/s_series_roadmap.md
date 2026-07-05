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
