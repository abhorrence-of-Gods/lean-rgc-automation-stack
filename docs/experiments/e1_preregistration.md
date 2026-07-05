# E1 Pre-Registration: Typed Failure Telemetry vs 1-bit Feedback

Status: registered before any E1 arm has been executed. The thresholds below
must not be edited after the first real-LLM episode is recorded; amendments
require a new section with a date and a reason.

## Hypothesis

Under an identical model, identical decoding parameters, identical instruction
text, and an identical per-theorem call budget, the typed-telemetry feedback
arm (a2) achieves a higher solve rate than the raw-error-text arm (a1), which
in turn is the strongest simple baseline above the 1-bit arm (a0).

## Arms

- `a0_onebit`: feedback is only the count of failed attempts.
- `a1_raw_error`: a0 plus up to 3 raw Lean error messages (500 chars each).
- `a2_typed_packet`: a0 plus the rendered prompt signal packet
  (`lean_rgc.pbct.signal_bridge`, all blocks included).

The only permitted difference between arms is the output of
`lean_rgc.evals.arms.render_feedback`.

## Protocol

- Tasks: 100 miniF2F-test theorems selected by `lean-rgc eval-subset --n 100
  --seed 0`, plus up to 50 project-local theorems as a contamination-aware
  secondary set, reported separately.
- Budget: 8 LLM calls per theorem per arm. Cached completions do not refund
  budget (the budget counts attempts, not network calls).
- Generator: one frontier API model, fixed model id, temperature 0.2,
  top_p 0.95, max 4 proposals per call. The model id and version are recorded
  in every boundary row and must be constant within one E1 execution.
- Audit: source_check lane, default success statuses of
  `lean_rgc.evals.harness`.
- Report: `lean-rgc eval-report` with `--n-bootstrap 10000 --seed 0`.

## Primary endpoint

Paired solve-rate delta a2 − a1 on the miniF2F subset.

Decision rule: the architecture thesis is supported iff the 95% bootstrap CI
of the paired delta excludes zero in favor of a2.

## Secondary endpoints (reported, not gating)

- Paired delta a1 − a0 (sanity: error text should beat 1-bit).
- audit_pass_per_call per arm (signal efficiency).
- Total prompt+completion tokens per solved theorem (cost efficiency).

## Pre-declared analysis on a negative or null result

If the primary endpoint fails, run packet-block ablations (drop one of
`last_failure`, `response`, `crg`, `safety`, `poms` at a time via
`include_keys`) on the same task subset before drawing conclusions; the
follow-up decision is made on which block, if any, carries the signal.

## Amendment 2026-07-03: factorial arm a3_typed_only (pre-registered before frontier E1)

Registered after the local-model pilot (Qwen2.5-7B-AWQ, n=60 mathd slice) and
before any frontier-model E1 episode. The pilot observed a1 == a0 exactly and
a2 − a1 = +0.217 with the 95% CI excluding zero, which makes the source of the
a2 effect (typed structure vs raw error content) the decisive open question.

- New arm `a3_typed_only`: identical to a2 except the packet's raw Lean
  message strings are dropped (`include_instance_messages=False`); aggregated
  typed blocks (status counts, observed response maxima) are kept.
- 2x2 reading: a0 = (no L, no G), a1 = (L only), a3 = (G only), a2 = (L + G),
  where L = raw instance messages and G = aggregated typed structure.
- Secondary endpoints: paired deltas a2 − a3 (unique value of instance text
  given structure) and a3 − a0 (value of structure alone), plus the
  interaction term a2 − a1 − a3 + a0.
- The primary endpoint of this document (a2 − a1 on the frontier run) is
  unchanged.

## Amendment 2026-07-05: conclusions SUSPENDED under authoritative labels

Three storage-time label defects (tagged-diagnostic mis-attribution,
dropped tagged errors, bulk syntax bleed/poisoning; see the G1 prereg
amendments c/e) corrupted the pilot solve labels this experiment's
episodes were computed from. Under the authoritative isolated re-audit
of every claimed-success row, the pilot7 arms become: a0 13/130,
a1 14/130, a2 13/130, a3 12/130 — every paired delta's CI includes
zero. The previously recorded conclusions (raw error text +19.2pt over
1-bit; typed-packet negative synergy) were artifacts of the label
defects and are WITHDRAWN. What survives: at authoritative labels the
7B generator solves ~10% of the miniF2F eval subset regardless of
feedback arm, and no feedback-format effect is detectable at n=130.
Any future feedback-arm claim requires a re-run on the fixed pipeline.

## Threats to validity acknowledged in advance

- miniF2F is likely in the generator's training data; this affects all arms
  equally and therefore does not invalidate the paired comparison, but
  absolute solve rates must not be quoted as generalization claims.
- Vendor model drift: an E1 execution must complete on one model version;
  episodes from mixed versions are excluded from the primary analysis.
