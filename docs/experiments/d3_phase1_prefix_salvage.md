# D3 Phase 1 Pre-Registration: verified-prefix salvage measurement

Status: registered before the registered analysis module runs and before
the G0c ground-truth calibration (the only genuinely new measurement).
Amendments require a new dated section.

FULL DISCLOSURE: the estimator design phase (2026-07-05 feasibility
workflow) already dry-ran a validated prototype on the complete retro
dataset; the outcome-gate thresholds below are therefore justified by the
Phase-2 cost model, NOT tuned blind, and the observed dry-run values are
shown next to each gate so the go/no-go is auditable. What this
registration adds: the reproducible house-style module, the G0 validity
gates (G0c pod calibration has NOT run), and the frozen decision reading.

## Question

For failed/partial whole-proof-script candidates, how much of each script
did Lean actually verify before the first error? High salvageable
fractions license suffix-conditioned repair (freeze verified prefix,
resample suffix) over whole-script resampling.

## Data and estimator

All non-success rows of the 12 working pilot run dirs (pilot3-pilot7
arms); the 7 broken-import dirs (pilot_a*/pilot2_a*/sanity_a1, 1,500
elab_error rows failing at line 1:0 on a missing module) are excluded —
no script elaborated there. Unit: deduped (task_id, tactic) candidate,
fresh rows preferred over cache replays (67% of rows are verbatim
replays).

Estimator (column-augmented, boundary-snapped; line granularity is
degenerate — 99% of scripts are single-line chained):
1. Reconstruct each bulk chunk's block offsets from lean_file grouping,
   micro_audit file order, deterministic block sizes (n_tactic_lines+5),
   and the header height H recovered per chunk from the 'by'-column
   anchor (predicted col = 35 + len(sanitized task_id) + len(statement)
   on the rendered theorem line; pilot-era renderer layout is
   byte-identical to HEAD).
2. Re-parse ALL stored message strings with a regex that also catches the
   tagged 'error(tag):' form missed at storage time; keep error-level
   locations inside the row's own block range (kills neighbor-block
   contamination); drop the theorem-line 'unsolved goals' anchor error.
3. No in-block error + partial with theorem-line loc -> f = 1.0
   ('complete_unsolved'). Error on/before the theorem line -> f = 0.
4. Else convert (line, col) to a codepoint offset into the script
   (col-2 for the render indent) and SNAP DOWN to the nearest tactic
   boundary (script start; after top-level ';' excluding '<;>'; before
   top-level ','; after newline; bracket depth over ([{⟨). 
   f = len(prefix.rstrip()) / len(script).

## Validity gates (all must pass before outcome gates are read)

- G0a anchor agreement: 'by'-column route and chunk-replay route agree on
  the theorem line for >= 99% of anchorable rows [dry run: 99.98%].
- G0b coverage: f defined for >= 95% of the deduped pool [dry run ~95%].
- G0c ground-truth calibration (NEW, on the pod): stratified sample of 60
  candidates with 0 < f < 1 (20 partial / 20 fail / 20 elab_error);
  re-audit 'frozen prefix + sorry' through the bulk executor. A prefix
  counts as verified iff the probe status is "unsafe" (sorry accepted =
  the prefix elaborated; any error status = broken prefix). Require
  >= 85% verified; 70-85% -> apply the measured downward correction to f
  before reading G1-G3; < 70% -> estimator invalidated, fall back to
  prospective measurement via the R0c block_start_line instrumentation.

## Outcome gates (frozen; dry-run values disclosed)

- G1 FULL license (suffix repair replaces whole-script resampling
  pool-wide): deduped median f >= 0.5. [Dry run: 0.185 -> expected FAIL.]
- G2 PARTIAL license (gated repair arm, runs only where the estimator
  says a majority prefix exists): share with f >= 0.5 is >= 25% AND
  median f among f > 0 is >= 0.5. [Dry run: 33.3% and 0.63 -> expected
  PASS.]
- G3 CONTINUATION arm (append tactics to a fully-elaborated script with
  goals remaining — a distinct intervention): share of f = 1.0
  ('complete_unsolved') >= 15% of the deduped pool. [Dry run: 21% ->
  expected PASS.]
- G4 NO-GO: G1 and G2 both fail -> whole-script resampling stands; D3 is
  re-measured free on the next run via R0c.

Sensitivity (reported, non-decisional): undefined rows imputed f=0;
replay-weighted instead of deduped; unsnapped char fraction as the upper
bound.

## Amendment 2026-07-05a: sibling-scan step restored

The condensed registration text omitted a step present in the validated
design recipe: recovering a row's first-error location from same-chunk
sibling rows (tagged-format error lines were stored under the previous
plain error's line key, i.e. possibly in a neighbor row's messages).
First execution WITHOUT it: coverage 94.83% — G0b fails by 0.17pt. With
the step restored per the original recipe: 16 rows recovered, coverage
95.47% — G0b passes. Both numbers disclosed; outcome statistics are
insensitive (median 0.185 -> 0.183, share f>=0.5 33.35% -> 33.29%).

## Amendment 2026-07-05b: G0c criterion re-operationalized

The registered proxy (probe status == "unsafe") was operationally broken
for two reasons discovered by the probe itself: (a) this toolchain's
sorry warning is emitted in the tagged format that the storage-time
regex misses, so a compiling single-goal probe lands as "success";
(b) `sorry` closes only the FIRST goal, so a compiling multi-goal prefix
lands as "partial" via the residual unsolved-goals error. Result under
the broken proxy: 0/60. The registered CONCEPT ("prefix compiles with
zero errors before the cut") is re-operationalized position-based on the
SAME probe artifacts: verified iff no error line falls within the
prefix-occupied block lines (exact via the R0c block_start_line
instrumentation, which the probe rows carry). No re-audit, no sample
change.

## Results 2026-07-05 (registered analysis + G0c calibration)

Report: `runs/d3_phase1/report.json`; probe rows:
`runs/d3_phase1/g0c_micro_audit.jsonl`. Deduped pool n=2,298.

- G0a PASS: anchor agreement 1,544/1,545 (99.94%).
- G0b PASS: coverage 95.47% (amendment a).
- G0c PASS: 58/60 = 96.7% of frozen prefixes compile cleanly before the
  cut (partial 20/20, elab_error 20/20, fail 18/20; both failures are
  `simp made no progress` inside the prefix — a context-sensitivity edge
  the splice must guard). Amendment b applies.
- G1 FAIL (as dry-run predicted): deduped median f = 0.183 < 0.5.
  Whole-script resampling is NOT replaced pool-wide.
- G2 PASS: 33.3% of candidates carry f >= 0.5; median over nonzero
  prefixes 0.63. The GATED suffix-repair arm is licensed.
- G3 PASS: 21.1% are complete_unsolved (f = 1.0). The append-continuation
  arm is licensed as a separate intervention.

Decision per the frozen rules: D3 Phase 2 proceeds as TWO gated arms —
suffix repair only where the estimator reports a majority prefix, and
continuation for fully-elaborated partials — not as a pool-wide
replacement. Design note carried forward: forcing multi-line scripts in
the generation prompt simplifies both the estimator and the splice.

## Threats acknowledged in advance

- f is an upper bound on usefulness: a compiling prefix can be
  semantically vacuous; the usefulness half is only measurable in Phase 2
  (repair success vs resample). G0c bounds only compile-cleanliness.
- Excluded undefined rows (~5%) are plausibly f-low; the impute-0
  sensitivity bounds this.
- Results describe the pilot3-7 generator (single-line chained scripts);
  a multi-line generation prompt in Phase 2 would simplify both estimator
  and splice — and shift f's distribution, so re-measure prospectively.
- The anchor constants pin the pilot-era renderer; any renderer change
  invalidates them for future retro use (prospective path is R0c).
