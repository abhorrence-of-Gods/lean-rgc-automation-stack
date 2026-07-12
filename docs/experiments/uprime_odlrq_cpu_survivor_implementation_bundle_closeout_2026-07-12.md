# U-prime / ODLRQ CPU-survivor implementation bundle closeout

Date: 2026-07-12 (Asia/Tokyo)

Status: **CLOSED BY THE FROZEN RESOURCE STOP RULE**

Controlling registration:
`docs/experiments/uprime_odlrq_cpu_survivor_implementation_bundle_amendment_2026-07-12.md`.

This is the single consolidated closeout permitted by section 8 of the
controlling amendment.  It records the implementation interval, the four
lane-qualified dispositions, the local resource-stop event, and the mandatory
nonclaims.  It does not reopen the U05 result, run a protected endpoint, or
license a retry.

## 1. Frozen implementation interval

The amendment anchor is:

```text
A_cpu = 9e126ce70f42944329ae361341f5934c1a569afe
```

The final implementation head is:

```text
C_cpu = ec7275d18755331285dc1b9ac4e9b5ccfbe13f17
```

`A_cpu..C_cpu` contains exactly three single-parent implementation commits:

| milestone | commit | disposition evidence |
|---|---|---|
| common admission | `94b1dec83b3a770015a11463b483623089c059d2` | strict synthetic finite admission, prohibited adapters, Windows runner, and topology guard |
| exact partition core | `231f42c2d88a5fc8c33c7df2c488b9ca2d8890eb` | exact Moore refinement, source-bound certificate, independent pair-relation verifier, full-member quotient, and shortest lexicographic witnesses |
| exhaustive qualification | `ec7275d18755331285dc1b9ac4e9b5ccfbe13f17` | exhaustive/permutation/adversarial qualification of the exact finite core |

No WP6-T, WP4-H, or WP4-W implementation commit belongs to the interval.  The
uncommitted WP6-T working files, including every edit made after the resource
stop, were discarded before this closeout was created.  Therefore the closeout
has `C_cpu` as its sole parent and changes only the two registered closeout
paths.

## 2. Four lane dispositions

| lane | final disposition | reason |
|---|---|---|
| `WP4-E` exact finite partition | **`CPU_EXACT_PARTITION_CORE_VERIFIED`** | common admission, exact producer/verifier, exhaustive oracle agreement, adversarial fixtures, local resource checks, and hosted CI were green at `C_cpu` |
| `WP6-T` tier firewall | **`CPU_SURVIVOR_PREREQUISITE_BLOCKED`** | the final registered local cap-owner qualification attempt reached the frozen 300-second wall before completion; no WP6-T code was committed |
| `WP4-H` bounded rational predictor | **`CPU_SURVIVOR_PREREQUISITE_BLOCKED`** | not started: the bundle-wide resource stop fired before milestone 5 was licensed |
| `WP4-W` componentwise window | **`CPU_SURVIVOR_PREREQUISITE_BLOCKED`** | not started: the bundle-wide resource stop fired before milestone 6 was licensed |

No lane is labelled `CPU_SURVIVOR_LANE_FAILED`.  In particular, the stop event
is not a semantic counterexample to the tier-firewall, Hankel, or componentwise
window hypotheses.

## 3. Qualified WP4-E evidence

The exhaustive qualification at `C_cpu` covered all 6,132 deterministic
binary-output Moore systems with `1 <= n_states <= 3` and
`1 <= n_actions <= 2`, embedded with absorbing `CLOSED` and `SINK` states and
all open seeds.  Every public admission/refinement/verification path agreed
with the independent restricted-growth-string partition oracle.  The suite
also covered permutation invariance, ID-versus-payload order, reverse hashes,
diamond and perturbation fixtures, trace/witness/source forgery, legacy
boundaries, a 64-state/12-action structural counter, 100-by-10 cap probes, and
UTF-8/coordinate resource failures.

Recorded local evidence for milestone 3:

```text
exhaustive-only: 1 passed, 54 deselected, 211.29 s
frozen runner:   exit 0, 55 passed, 252.75 s
full repository: 2400 passed, 3 skipped, 161 deselected, 921.51 s
```

Hosted CI was green for every committed milestone:

| commit | hosted CI |
|---|---|
| `94b1dec83b3a770015a11463b483623089c059d2` | run `29173170354`, job `86597551727`, success |
| `231f42c2d88a5fc8c33c7df2c488b9ca2d8890eb` | run `29174823088`, job `86602017434`, success |
| `ec7275d18755331285dc1b9ac4e9b5ccfbe13f17` | run `29176248416`, job `86605869533`, success |

## 4. WP6-T diagnostic work and the stop event

WP6-T remained an uncommitted candidate throughout.  Its diagnostics are
reported to explain the stop, not to qualify or preserve that implementation.

An earlier candidate, before the last two resource-bound repairs, completed the
frozen runner:

```text
command: & .\tools\run_uprime_cpu_survivor_tests.ps1
exit:    0
result:  68 passed in 204.39 s (0:03:24)
```

That execution is **not** evidence that the later timeout candidate had
identical bytes.  After it, the candidate added direct signed-64 interval-target
validation and a pre-allocation combined 250,000-work-unit extension check.
The later resource-fixed, pre-serializer candidate had these local diagnostics:

```text
WP6-T targeted:       14 passed in 1.89 s
manifest / identity:  48 passed in 17.56 s
```

The registered local cap-owner runner was then executed on that later
candidate:

```text
command: & .\tools\run_uprime_cpu_survivor_tests.ps1
runner timeout class: 124 (`$ExitTimeout` in the frozen script)
outer agent report:   nonzero exit 1
output:  ............................................
         uprime-cpu-survivor: 300-second wall limit exceeded; Python was terminated
```

The execution transcript available to this closeout preserves the outer
agent's nonzero `1` report, while the frozen runner source assigns this exact
timeout branch class `124` and exits with that value.  This reporting-layer
difference does not change the adjudication: the identifying timeout message
and 300-second termination are unambiguous.  No pytest assertion or contract
failure was reported before termination.  The run nevertheless exhausted the
explicit wall owned by the frozen runner in section 9.  Section 10.2's
bundle-stop and no-extension rules therefore required an immediate stop,
prohibited a retry, and prohibited milestones 5 and 6.

An independent adversarial reviewer also identified a serializer fail-closed
defect: low-level post-construction mutation could make a capability's public
`to_dict()` emit altered visible fields even though its decoder and downstream
gate rejected them.  A hardening patch and mutation tests were drafted only
after the timeout.  They are outside the licensed interval, were not used to
adjudicate this bundle, and were discarded with all other uncommitted WP6-T
files.

Accordingly, this closeout does not claim `CPU_TIER_FIREWALL_VERIFIED`.  The
resource stop establishes only that WP6-T qualification was not completed
within the preregistered local envelope.  It does not establish that the
underlying tier separation is mathematically impossible.

## 5. Resource and exposure accounting

- Execution used local Windows CPU only.
- No SSH, GPU, CUDA, model server, native Lean subprocess, production RPC, or
  LLM proposer was used.
- No U05 result path, consumed artifact, root quarantine file, reserved task,
  or canonical RPC input was reopened.
- No M5/Hankel or M6/componentwise implementation was started.
- No additional ledger, CAS, recovery, publication, component amendment, or
  result triplet was created.
- The local timeout was retained as a blocking result; neither the 300-second
  wall nor the semantic test set was weakened.

## 6. Mandatory nonclaims and next authority boundary

This closeout licenses no K1--K4 protected result, U'2--U'5 claim, production
hard operator, finite-horizon envelope, MaxEnt law, predictive/positive global
similarity, Lean-oracle learner, solve-rate claim, GPU work, SSH work, or LLM
distillation.  The exact finite core remains synthetic-development evidence
under its registered response vocabulary; it is not a complete Lean reachable
domain or an all-germ quotient.

The current CPU-survivor bundle is closed and cannot be extended by a small
amendment.  Any future work must begin under a genuinely new registered phase
that treats this resource stop and the excluded serializer defect as inputs,
without reclassifying this closeout or claiming the uncommitted WP6-T code as a
result.
