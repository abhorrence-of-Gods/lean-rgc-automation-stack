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

## Threats to validity acknowledged in advance

- miniF2F is likely in the generator's training data; this affects all arms
  equally and therefore does not invalidate the paired comparison, but
  absolute solve rates must not be quoted as generalization claims.
- Vendor model drift: an E1 execution must complete on one model version;
  episodes from mixed versions are excluded from the primary analysis.
