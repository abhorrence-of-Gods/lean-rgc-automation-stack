# U-prime / ODLRQ lane-isolated recovery closeout

Date: 2026-07-12 (Asia/Tokyo)

Status: **CLOSED WITH THREE INDEPENDENT VERIFIED LANE DISPOSITIONS**

Controlling registration:
`docs/experiments/uprime_odlrq_lane_isolated_recovery_amendment_2026-07-12.md`.

Mathematical-direction correction:
`docs/experiments/uprime_odlrq_m5_two_sided_hankel_closure_amendment_2026-07-12.md`.

This is the single consolidated closeout permitted by the controlling
amendment.  It records three independent synthetic finite development
dispositions; it is not a scalar portfolio pass.  It changes only this new
document, has implementation head `617f4b3c6283d4c64b911d65fc0feb2a6c5f0509`
as its sole parent, and neither reopens a protected result nor licenses a new
execution.

## 1. Frozen authority and implementation interval

The predecessor CPU-survivor bundle remains closed at:

```text
92b34496d3f2455a63e05791b7a0342050c49bcd
```

The recovery interval is governed by these commits:

| role | commit | adjudication |
|---|---|---|
| recovery amendment | `2712060ff5b0223aa581dd611363dba517520048` | registered the lane-isolated phase |
| control-plane successor | `40cb97a8bac94e17538958c33c53b2f2c758b0f5` | repaired only the post-closeout guard lifecycle and was green before M4 |
| M4 / WP6-T semantic commit | `9f67edeff33c77a756788c29023f693d1bad8ab8` | recovered the exact/certified/observed/nominal tier firewall |
| M5 direction correction | `a749613a22f979f79b1096eb99f5721bde7fc1a3` | froze two-sided Hankel closure before M5 execution; not a semantic lane commit |
| M5 / WP4-H semantic commit | `bdad87c92329c33acd2e99659b3eb10f77611c8c` | recovered the bounded rational predictive core |
| M6 / WP4-W semantic commit | `617f4b3c6283d4c64b911d65fc0feb2a6c5f0509` | recovered the componentwise finite-memory diagnostic |

Each lane used exactly one semantic commit and no same-lane repair commit.
Every semantic diff matched its five-path allowlist and appended exactly its
own unit-test row to `tests/tier_manifest.json`.  The M3 partition dependency,
the U05 result package, the controlling documents, and the identity guards
remained immutable except for the two explicitly registered control-plane
transitions above.

## 2. Historical CI adjudications retained for future readers

### 2026-07-12 U05 result-publication badge

The immutable U05 result-publication commit
`cc91a4181a9f87ec10f11727ed787eb7149f955a` has red GitHub Actions run
`29166670576` (job `86580832840`).  The dated audit determined that the failure
was caused by the identity guard's shallow-history design omission, not by a
probe, prerequisite, artifact-integrity, or scientific-result failure.  The
exact scientific candidate at `3bb3408afc50a08307cff2c9b1906a299739dfb5`
had green GitHub Actions run `29166073728` (job `86579287017`).  The red
result-commit badge therefore must not be interpreted as a failed scientific
execution.  The consumed look, immutable result values, result commit, and
rerun prohibition remain unchanged.

### 2026-07-12 recovery-amendment control plane

The recovery amendment itself had red run `29178759991` (job `86612624356`)
because the original identity guard continued applying a dirty-worktree rule
after the registered old closeout.  That was a distinct guard-lifecycle defect,
not an M4--M6 scientific failure.  The narrowly registered successor
`40cb97a8...` repaired that lifecycle and had green run `29179085848` (job
`86613437020`) before any lane semantic work began.  The M5 direction
correction `a749613a...` likewise had green run `29182087953` (job
`86621544946`) before the M5 candidate was executed.

## 3. Independent lane dispositions

| lane | final disposition | bounded meaning |
|---|---|---|
| M4 / WP6-T | **`CPU_TIER_FIREWALL_VERIFIED`** | source-bound synthetic exact quotient export, independently evidenced interval capability, observed/nominal separation, serializer rederivation, and fail-closed gates |
| M5 / WP4-H | **`CPU_HANKEL_PREDICTIVE_CORE_VERIFIED`** | bounded exact-rational Hankel construction with two-sided row-prefix/column-tail closure, shift consistency, resource caps, and present-class-only ablations |
| M6 / WP4-W | **`CPU_COMPONENTWISE_DIAGNOSTIC_VERIFIED`** | bounded reverse-`CanClose` diagnostic with separate occurrence/state populations, strict componentwise contraction, and all-prefix overshoot |

These are independent dispositions.  No lane failure was hidden by aggregation,
and no lane's success promotes another lane or the complete upper stack.

## 4. Final Windows-CPU qualification

All three dedicated runners were re-executed at the final implementation head
on local Windows CPU.  Each runner retained its frozen test, hard wall,
qualification margin, 2 GiB working-set cap, 64 MiB captured-output cap, hidden
receipt, native-exit match, and subprocess/exec/forced-exit denials.

| lane | semantic pytest | qualification elapsed | peak working set | frozen qualification gate |
|---|---:|---:|---:|---:|
| M4 / WP6-T | 24 passed in 5.92 s | 7.958 s | 58,150,912 B | at most 10 s |
| M5 / WP4-H | 27 passed in 7.39 s | 9.425 s | 55,549,952 B | at most 20 s |
| M6 / WP4-W | 23 passed in 2.71 s | 4.304 s | 55,296,000 B | at most 10 s |

The final cold M6 candidate qualification independently recorded 23 passed in
2.85 s, qualification elapsed 4.570 s, and peak working set 58,806,272 B.
At the accepted implementation head, the recovery identity suites reported 44
passed and the tier-manifest suite reported 5 passed.  The exhaustive M3 suite
was deliberately not embedded in any lane runner; its immutable blobs and
ordinary hosted CI supplied that dependency, as preregistered.

## 5. Hosted CI evidence

Candidate and accepted-branch CI were independently green for every semantic
lane commit:

| lane commit | candidate CI | accepted CI | accepted full-suite summary |
|---|---|---|---|
| M4 `9f67ede...` | run `29180309960`, job `86616586904`, success | run `29180392495`, job `86616794821`, success | 2,421 passed, 7 skipped, 161 deselected |
| M5 `bdad87c...` | run `29182259813`, job `86622020646`, success | run `29182367792`, job `86622325595`, success | 2,448 passed, 7 skipped, 161 deselected |
| M6 `617f4b3...` | run `29183387234`, job `86625064713`, success | run `29183514631`, job `86625428743`, success | 2,471 passed, 7 skipped, 161 deselected |

The M5 correction CI and both M5 semantic CIs came after the correction was
frozen.  No failed candidate was fast-forwarded to the accepted branch, and no
commit quota was transferred between lanes.

## 6. Repair and deviation accounting

- M4 was a clean reimplementation, not a resurrection of the discarded old
  candidate.  It included serializer rederivation from retained authorities,
  signed-64 interval-target validation, and the pre-allocation 250,000-work-unit
  bound identified by the earlier audit.
- Before M5 execution, adversarial review found that one-sided reconstruction
  could seal a shift-inconsistent table.  The dated `a749613a...` correction
  froze row-prefix and column-tail closure, shift consistency, and optional
  present-class ablations without changing the data source, caps, or endpoint.
- M6 required no amendment or same-lane repair.  Its one semantic commit
  implemented reverse `CanClose`, nonempty OPEN-only continuations, distinct
  occurrence and immutable-state denominators, strict five-coordinate
  contraction, and overshoot over every prefix including noncontracting words.
- No new evidence ledger, CAS, fake publisher, or per-unit preregistration
  triplet was added.  This phase returned effort to the registered measurement
  substrate rather than extending evidence-governance machinery.

## 7. Resource, exposure, and quarantine accounting

- Semantic construction and qualification used local Windows CPU only.
- Network use was limited to Git push and read-only hosted-CI inspection.
- No SSH session, remote CPU, GPU, CUDA, model server, LLM proposer, native
  Lean/RPC production call, or protected endpoint was used.
- The U05 result, reserved tasks, external NS numerical results, and excluded
  root inputs were not reopened as evidence for these lanes.
- `llm_local.json`, `pilot_tasks.json`, `fake_lean_smoke.py`, and
  `smoke_tasks_local.jsonl` are outside the repository in
  `$HOME/.codex/quarantine/lean-rgc/uprime-deferred-2026-07-12/`.  They were not
  read by this phase and were not converted into EvidenceLedger records.
- LLM proposal or knowledge distillation remains out of scope until the exact
  generator and upper stack have independently qualified and a fresh amendment
  explicitly registers that later question.

## 8. Mandatory nonclaims and next authority boundary

This closeout licenses no protected K1--K4 result, depth-four result,
production Lean locality claim, complete all-germ quotient, hard fiber
envelope, MaxEnt fit, global-similarity certificate, learner improvement,
solve-rate claim, deployment, SSH/GPU work, or LLM proposer/distillation.  It
also does not claim a production Lean reachable-domain quotient, MaxEnt safety,
predictive/positive global similarity, global Hankel rank stabilization, or
validity beyond the frozen synthetic finite fixtures.  M5 supplies predictive
development machinery, not safety; M6 is a diagnostic, not a certificate.
Exact, robust, observed, and nominal evidence remain distinct.

The next candidate remains the name-only registration from the controlling
amendment:

```text
U'1.5-KP3-D4-CANONICAL-HISTORY
provenance: fiber_closure_generator_part2
```

It may import only completed structural techniques, never the NS numerical
values as Lean evidence.  A fresh committed, pushed, and green amendment must
freeze the Lean-specific normalization congruence, witnesses, generation-time
provenance, raw-versus-normalized depth-at-most-3 equality regression, response
channels, task seeds, caps, and stop rules before depth four is run.  Only after
that feasibility decision may a separate locality-learning or upper-stack
construction phase begin.  This recovery interval is closed and cannot be
extended by adding another M4--M6 semantic commit.
