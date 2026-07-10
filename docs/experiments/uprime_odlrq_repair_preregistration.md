# U' / ODLRQ repair pre-registration

Status: PUBLIC REDACTED DERIVATIVE of locally frozen v0 (raw SHA-256
`888CE640A731A4D153C87C0E5F3EFD879C5073365B027902C73D465AA9CB98B2`).
The local freeze and first K0 result enter Git together, so K0 is an unanchored
development pilot, not an externally timestamped confirmatory run. Every
future amendment must be committed and pushed before its first protected
execution.

This v0 registration licenses only U'-1, U'0, the deterministic part of U'1,
and the K0 pilot below. It does NOT license K1--K4 confirmatory gates, U'2
envelope deployment, U'3 MaxEnt fitting, U'4 similarity deployment, U'5 sealed
evaluation, GPU training, or a performance claim. Any such execution requires
a dated amendment made before reading its protected outcomes.

The adjudication record is
`docs/experiments/uprime_odlrq_adversarial_review_2026-07-10.md`.

## Objective

Determine, as cheaply and fail-closed as possible, whether the proposed
worst-case-envelope -> MaxEnt -> global-similarity and ODLRQ program has a
sound, non-vacuous substrate worth scaling.

The order is deliberately:

```
U'-1 mathematical repair
-> U'0 semantic identity/environment contract
-> U'1 transition metrology repair
-> K0 deterministic foundation probes
-> dated K1--K4 confirmatory-freeze amendment
-> only then U'2/U'3/U'4 and GPU work
-> U'5 all-task paired evaluation last
```

## Evidence classes and contamination

1. The previously inspected 103 score-side tasks and current phi/alpha are
   `development_contaminated`. They may falsify engineering proposals but may
   never support U'5.
2. Existing pilot/G1/S' artifacts remain historical/development evidence under
   their registered amendments.
3. miniF2F-valid is reserved for later confirmation. The known three-row
   `_tmp_minif2f_valid3.jsonl` exposure is excluded. This v0 run MUST NOT read
   any other valid-split result.
4. The public benchmark nature of miniF2F does not certify absence from an LLM's
   pretraining data. Any future model-performance claim must label this
   limitation and, where possible, include a separately generated/private task
   stratum.
5. `ObservationFrameId` is immutable coordinate provenance. Read/burn status is
   stored only in an append-only `EvidenceLedger`; it is not a FrameId field.

## Frozen semantic records

The repaired system will use three separate identifiers.

### ObservationFrameId

```
environment_content_digest
source_lane
granularity
coordinate_schema_digest
normalization_id
extractor_version
```

### TransitionSemanticsId

```
lean/compiler build identity
dependency/import closure digest
action grammar version
target-site convention
premise/simp/typeclass whitelist digest
transparency/options
effective per-action and remaining episode budget
proposer PolicySemanticsId when proposals are in scope
```

### EvidenceLedger entry

```
artifact/task id
evidence class
append-only read event
reader/purpose
timestamp
parent commitment/hash
burn/retirement status
```

Historical rows lacking an exact record are labelled `frame_estimated` and may
not enter a hard tier.

## Work packages authorized by v0

### U'-1: theory errata

Required deliverable: an errata/amended theory record that:

1. unifies the weighted compression/lifting/envelope coordinates;
2. replaces unconditional projection composition/commutativity by explicit
   nested/Markov assumptions or a measured composition defect;
3. includes cross covariance or proves the conditional-independence and
   sufficiency conditions used to remove it;
4. transports projected similarity to one frozen true target with a computable
   residual bound;
5. turns the joint certificate into an operator telescoping with all constants,
   domains, norms, and model residuals defined;
6. states MaxEnt feasibility/support/identifiability conditions and separates
   moment fit from operator accuracy;
7. uses finite-horizon positive messages whenever `rho(M) < 1` is unavailable.

U'-1 gate `T0`: every legacy finite counterexample in K0 must fail under the
legacy formula and pass (or be explicitly out of scope under a stated
hypothesis) under the amended formula. No theorem may be promoted by empirical
`violation == 0` alone.

### U'0: environment, frame, and cache identity

Required changes:

- one content-sensitive environment digest shared by audit queue, result cache,
  Lean server, persistent worker, and kernel-state records;
- local source/build content, dependency manifest, resolved Lean version,
  imports, and relevant options included;
- separate collision-resistant full canonical signature and fast hash;
- local-context/boundary content included in state identity;
- registered FrameMorphism only between explicitly named observation frames;
- all new U' records strict on unknown semantic fields.

U'0 deterministic gates:

`F0` changing any imported/local source or `.olean` content changes the
environment digest; a rebuild with byte-identical semantic artifacts does not.

`F1` two commuting paths to the same syntactic/gauge-normalized state have the
same full key; hash equality is followed by full comparison.

`F2` any litmus pair with a different response to a frozen primitive action has
different state/observation identity. In particular local-context changes that
alter `exact h`, typeclass, or frozen-simp behavior may not collide.

`F3` mismatched coordinate keys, normalization, granularity, or semantics IDs
raise a hard error on new U' paths. No truncation/padding fallback is allowed.

### U'1: transition metrology

This v0 licenses only the bounded primitive fragment

```
intro
constructor
explicit exact
explicit apply from a frozen premise whitelist
frozen simp only
explicit target mvar
```

Occurrence-targeted `rw`, unrestricted `simp`, `aesop`, and `omega` remain
opaque or deferred until separately registered.

U'1 deterministic gates:

`M0` replay certificate is `verified` only after an independent replay matches
the full post-state signature; otherwise it is `failed`/`unknown`, never
`pending` promoted as pass.

`M1` effective max-heartbeats and remaining episode budget are part of the
transition semantics and cache key, and the telemetry reports the same values
the runtime enforced.

`M2` `assigned_mvars` is a before/after difference; all goals are swept for
side-effect assignments; closed/new goal sets are exact on the litmus suite.

`M3` failed/partial transitions retain the boundary/read evidence actually
available. Final proof-term `minimal_support` is not relabelled as an exact
action read set.

`M4` timed-out workers are discarded or resynchronized by checked request IDs;
orphan responses cannot be consumed by the next request.

## K0 CPU foundation pilot (licensed now)

K0 is a deterministic, non-evidential engineering pilot. It may use only
synthetic finite examples, source-level contracts, temporary projects, and
already-contaminated development artifacts. Its purpose is to expose blockers,
not to license U'2.

Frozen probes:

`K0-W` legacy weighted-lifting counterexample and corrected-coordinate check.

`K0-P` direct-vs-adjacent conditional-kernel counterexample and contextual
projection order counterexample.

`K0-C` full covariance vs diagonal-only covariance counterexample.

`K0-E` mutate same-named `.olean` bytes in a temporary project; the current
environment fingerprint must be reported content-sensitive or blocked.

`K0-R` report replay/heartbeat/delta contract status from the current native
RPC without treating a stub/null field as a pass.

K0 stopping rule: run each probe once after the code and this registration are
hashed. Any blocker yields overall `BLOCKED_AS_WRITTEN`; no tuning or rerun may
convert it to PASS. Repairs are evaluated only by a new code revision and a
dated execution record preserving the original result.

K0 outputs:

```
runs/uprime_k0_20260710/foundation_probe.json
runs/uprime_k0_20260710/environment_fingerprint.json
```

## K1--K4 pilot and confirmation rule (not yet licensed)

The later probes are named now to prevent replacement after K0, but v0 does not
freeze their confirmatory numerical thresholds:

- `K1`: exact compression/index after identity repair;
- `K2`: productive-trajectory finite-horizon envelope reachability,
  non-vacuity, and ranking effect;
- `K3`: action-prefix-closed Hankel rank growth and `sigma_r` conditioning;
- `K4`: true-target residual, cross-covariance inflation, and similarity
  coverage.

Procedure: first run a budget-capped pilot on development-contaminated/synthetic
data. Archive its estimands and costs. Without reading any reserved/valid-split
outcome, add a dated Amendment A freezing sample sizes, numeric gates, query
budgets, look count (one), failure branches, and GPU budget. Only Amendment A
can license confirmatory K1--K4 or U'2 construction.

## U'2--U'5 endpoint obligations (registered now, execution blocked)

- The hard envelope is a pre-action resource/debt admissibility claim over a
  declared bounded fragment and horizon, not logical proof soundness (the Lean
  kernel already adjudicates proof terms).
- MaxEnt is evaluated by a frozen proper prediction/risk endpoint and baseline;
  it is never credited as a safety source.
- U'4 must report coverage and the proved/estimated true-target residual. A
  learned `L_+` or zero sample violations is statistical-only.
- U'5 primary endpoint is paired solve-rate over the full identical task set
  under equal global budgets. Zero-action/abstention tasks remain in the
  denominator. Wall time, heartbeats, LLM calls, coverage, abstention, and
  certificate violations are co-reported. No pass-on-selected-actions endpoint
  is admissible.

## Execution placement and resource gate

### Windows CPU (authorized)

Use the current Windows workspace for U'-1/U'0/U'1 unit/litmus work, K0, small
reachable fragments, cache/RPC verification, and all prereg/report generation.

### Remote RTX 4090 host (fingerprint authorized; build blocked)

Registered private endpoint alias:

```
UPRIME_GPU_HOST
```

Exact SSH coordinates and the observed host key are stored outside the public
repository. The 2026-07-10 read-only fingerprint found Ubuntu 24.04.4, RTX 4090 24GB,
driver 580.159.04, CUDA/nvcc 13.0, 80 logical CPUs, 251 GiB RAM, and about
24 GiB usable overlay free space. `/workspace` has no project checkout.
A reserved remote listener is already occupied by Jupyter, so no U' service
may bind it; the supplied local forward targets that existing service only.

No clone, install, model download, training, or persistent remote process is
licensed by v0. Before Amendment A can authorize GPU work it must freeze:

1. repo commit/tree hash and clean-worktree rule;
2. off-pod artifact destination and checkpoint cadence;
3. exact Python/CUDA/PyTorch/model/tokenizer/weights digests;
4. disk budget below the measured 24 GiB free-space ceiling or a newly mounted
   persistent volume;
5. command, seed set, concurrency/batching policy, wall-time/VRAM stop limits;
6. result encryption/read ledger for any protected evaluation.

## Failure branches

- Any `T0/F0--F3/M0--M4` failure: remain in repair; K1--K4 and GPU work blocked.
- K1 shows no nontrivial compression: terminate ODLRQ quotient investment;
  retain only metrology/frame repairs and registered S'3 work.
- K2 is always closed or ranking-invariant: terminate envelope deployment;
  retain runtime budget/rollback monitoring.
- K3 rank does not stabilize or is ill-conditioned: terminate finite predictive
  quotient claim; retain exact bounded traces only.
- K4 lacks residual/covariance coverage: terminate hard global-similarity claim;
  prediction may continue only as statistical-only under a new registration.
- A GPU resource or provenance prerequisite fails: do not improvise on the pod;
  archive the fingerprint and return to local planning.

## First execution command

After the K0 implementation lands, the frozen local command is:

```
python -m lean_rgc.evals.uprime_k0 \
  --repo-root . \
  --out runs/uprime_k0_20260710/foundation_probe.json
```

The command and output are recorded without post-hoc threshold changes.
