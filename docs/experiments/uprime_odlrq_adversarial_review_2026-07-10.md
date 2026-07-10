# U' / ODLRQ adversarial review record (2026-07-10)

Status: REGISTERED REVIEW RECORD. This document records the independent
Codex multi-agent adjudication completed before any U' repair experiment was
launched. It supersedes the external integrated review wherever the two
conflict, but does not erase that review or its individual findings.

## Reviewed material and provenance

- Theory source: original UTF-8 bytes SHA-256
  `7E24F7D444A263792A3A717B1C26807D0A15626C2A11D8F38A1DCCB7DE69CD87`.
  The repository-readable normalized copy is
  `docs/external/uprime_odlrq_adversarial_review_2026-07-10/fiber_closure_fixed_point_integrated_jp.tex`,
  SHA-256
  `7E24F7D444A263792A3A717B1C26807D0A15626C2A11D8F38A1DCCB7DE69CD87`.
- Proposal transcript: original UTF-8 bytes SHA-256
  `855F49956CABAE786FA221B4D7D38E95630147687A79941FB17F0C0D1137E9AB`.
  Its path-pseudonymized public derivative is
  `docs/external/uprime_odlrq_adversarial_review_2026-07-10/proposal_transcript.public.txt`,
  SHA-256
  `D407AF185EAEFF4E9339814DAD35B30CA7B8225E17260EDA340CB9F87770D9A7`.
- The public external-review subset is in
  `docs/external/uprime_odlrq_adversarial_review_2026-07-10/` as
  `parsed_review.public.json` and `review_brief.public.md`. The raw workflow is
  retained investigator-local because it embeds workstation paths; its raw
  SHA-256 remains recorded in the execution log.
- Repository state reviewed at commit `b4b81be` plus the pre-existing dirty
  worktree disclosed by `git status`; no pre-existing user file was modified
  during the review.

The review used independent math/endpoint, similarity, Lean metrology, and
governance lenses. Findings were checked against the TeX equations, source
lines, finite counterexamples, and focused tests. The external review's
`27 confirmed / 11 refuted` count is not treated as a vote: its `confirmed`
bucket retains attacks whose headline or severity was substantially corrected
by the validator whenever some residual concern survived.

## Verdict

The current theory/program freeze is REJECTED AS WRITTEN.

The rejection is not merely an implementation/governance rejection. Several
load-bearing identities in the current TeX are false without missing
assumptions, and the global-similarity endpoint does not yet transport its
projected certificate to the true target. These are freeze blockers even
before the confirmed RPC/cache/governance defects are considered.

This is not a verdict of principled impossibility. Weighted block domination,
finite-horizon memory bounds, the hard/robust/nominal separation, bounded-
fragment action-word closure/Nerode theory, and counterexample-directed CEGAR
survive. They may be re-registered after the obligations below are discharged.

## Mathematical freeze blockers

### R1. Weighted envelope and lifting use incompatible coordinates

TeX lines 746--759 define a positive envelope for the weighted microstate
mass containing `omega(T') / omega(T)`. Lines 826--848 then use the unweighted
compression and lifting

```
(C x)_Q = sum_T x_T
(L_mu z)_T = z_Q mu_Q(T).
```

One source, one target, `A = 10`, `omega_source = 100`,
`omega_target = 1`, and `mu = delta_source` give `M = 0.1` but
`K_mu = C A L_mu = 10`. Hence the stated `|K_mu z| <= M |z|` is false.

Repair obligation: either freeze `omega == 1`, or use a consistent weighted
pair such as

```
C_omega x = sum_T omega(T) x_T
(L_{mu,omega} z)_T = z_Q mu_Q(T) / omega(T),
```

and re-derive every MaxEnt/KL operator in those coordinates.

### R2. Kernel factorization and the written contextual order identity are not exact

TeX lines 545--577 assert both an adjacent-kernel product identity and an
order-independence identity for exact contextual projections. For independent
bits `X,Y`, taking `R0=X, R1=Y, R2=X` makes the direct `R0 -> R2` channel the
identity while the adjacent product averages to zero. With the TeX definition
`P_{v|S} = E[. | G_{S union {v}}]`, tower gives
`P_{w|S,v} P_{v|S} = P_{v|S}` while the swapped side is `P_{w|S}`; equality
therefore requires those two retained-information projections to agree. This
written order-independence failure is distinct from a generic commutator test.

Repair obligation: require an explicitly nested filtration or a proved
Markov/sufficiency/separator condition. Otherwise the adjacent product must be
declared an approximation and its composition defect must enter the error
budget.

### R3. The global covariance equation drops cross terms

TeX lines 1188--1204 identify

```
Cov(sum_v a_v zeta_v | H_R) = sum_v a_v^2 A_R(H_v)
```

without conditional independence and local-sufficiency hypotheses. With two
vertices, `zeta_1 = zeta_2 = Z`, `Var(Z)=1`, and unit weights, the left side is
4 and the right side is 2. The reverse-martingale orthogonality proved earlier
is relative to a different filtration and is not preserved by arbitrary
reconditioning on `H_R`.

Repair obligation: retain pair/path/hyperedge covariance (including shared
mvar/typeclass dependencies), or prove the exact conditional-independence and
sufficiency hypotheses used to remove it.

### R4. Similarity controls only the projected model

The Wasserstein expression in TeX lines 1160--1178 leaves an uncontrolled
`epsilon_R(T) - epsilon_R(S)`. The bisimulation fixed-point result in lines
1207--1232 controls values generated by the same projected `(ell,P)`, not the
original full target. Two hidden states may have projected distance zero and
opposite true tail values.

Repair obligation: prove and freeze a transport statement of the form

```
|V_true(T) - U(q(T))| <= epsilon_projection(T)
```

with an independently computable upper bound. Node/edge measures are sufficient
only for a scoped node/edge-additive target unless longer path residuals are
also bounded.

### R5. The joint certificate is not yet a falsifiable composition theorem

TeX lines 1574--1596 add projection, boundary, semigroup, similarity, and an
unconstrained `epsilon_model` without defining a common target/norm or the
transport constants. The residual can absorb the entire true error.

Repair obligation: construct an operator telescoping for one frozen target,
define every constant and domain, and make `epsilon_model` an independently
bounded quantity rather than a fitted remainder.

### R6. MaxEnt moments do not imply operator accuracy

Moment agreement in TeX lines 852--870 does not establish the later assumed
`delta = ||K_true - K_ME||`. A two-point fiber with a constant registered
statistic has zero moment error while its transition load can differ by one.

Repair obligation: freeze the reference law/statistics before outcome reads
and either include the operator load in their controlled span or directly bound
operator/TV/KL error on held-out fibers. A zero empirical upper-bound violation
cannot be promoted to the hard tier without proved global `L_+`, certified
upper labels, and coverage.

## Lean/metrology freeze blockers

### C1. Current normalized identities are neither path-invariant nor complete

- `norm_hash` numbers mvars by creation/history order and hashes rather than
  comparing full canonical signatures.
- goal/mvar normalized hashes omit the local-context content needed to
  distinguish states whose response to `exact h` differs.
- universe-level mvars and indirect assignments are not fully normalized.

No compression or exact-quotient result may use these keys. The replacement
must have separate `StateIdentityKey` and `BehavioralObservationKey` types,
full-signature comparison after hash match, and commuting-path plus
different-response litmus tests.

### C2. Existing project/cache fingerprints are not semantic environment IDs

`audit_result_cache.workdir_fingerprint` hashes the toolchain/manifest text and
only the set of top-level `.olean` names. The current test suite explicitly
expects a changed `.olean` payload with the same name to retain the same
fingerprint. Other queue/server/kernel paths implement still different project
fingerprints.

`make_audit_cache_key` is task/state/action-specific and therefore is not a
FrameId. Only some of its components are reusable. Environment identity must
include actual local source/build content, compiler build identity, dependency
manifest, imports, and relevant option/action semantics.

### C3. Runtime budget and cache semantics disagree

The persistent RPC reads `action.max_heartbeats`, persists the resulting option
in the child state, and inherits it when the next action omits the field. The
cache key instead falls back from a missing action value to
`task.max_heartbeats`, which the stateful RPC path does not apply. Thus a cache
key can describe a different transition budget from the one executed.

### C4. Required telemetry remains incomplete

Replay certificates are always `pending`; heartbeat consumption is null;
`assigned_mvars` is cumulative rather than newly assigned; assigned tail goals
are not swept from the goal queue; state serialization is global and the state
map is insert-only. `minimal_support` is useful final-proof support, but is not
an exact read set for partial/failed tactics and truncates constants.

### C5. Proposer semantics and evidence provenance are separate contracts

The LLM prompt cache intentionally excludes provider identity and has no model
weights/tokenizer/server/quantization digest. This does not invalidate replay
of a fixed logged Lean action, but it prevents the proposer policy from being a
sealed U'5 semantic object. It belongs in `PolicySemanticsId`, not in the Lean
state identity alone.

## Governance adjudication

- The current repository has no append-only read/burn ledger. This part of the
  external review is confirmed.
- `exposure_class` must not be embedded in immutable `FrameId`: burn status is
  mutable evidence state. Freeze separate `ObservationFrameId`,
  `TransitionSemanticsId`, and `EvidenceLedger` records.
- Selective evaluation is not structurally unavoidable. The existing eval
  harness records every task, counts zero-action/abstention tasks as unsolved,
  and supports paired solve-rate over identical task sets. U'5 must bind to
  that all-task denominator and report coverage/abstention and equal-budget
  cost alongside solve rate.
- Thresholds, refinement/query budgets, look counts, proposer policy, and all
  failure branches must be frozen before any sealed result is read.

## Surviving scope

The following may be used in a repaired program, subject to their hypotheses:

1. weighted block domination within one consistent coordinate convention;
2. hard/robust/nominal certificate labels and the rule that MaxEnt is not a
   source of safety;
3. finite-horizon return-memory bounds with the episode horizon frozen;
4. bounded-fragment action-word closure and finite reachable-subsystem Nerode
   refinement;
5. exact counterexamples from the Lean oracle in the CEGAR split direction;
6. separate prediction and safety metrics, provided the safety Lipschitz and
   coverage obligations are proved rather than fitted;
7. existing branch/rollback and explicit-target-mvar substrate.

## Disposition

Execution is transferred to
`docs/experiments/uprime_odlrq_repair_preregistration.md`. No U'2--U'5 claim is
licensed by this review record. The first authorized work is mathematical
errata, semantic identity/cache repair, transition metrology repair, and
non-evidential CPU kill probes.
