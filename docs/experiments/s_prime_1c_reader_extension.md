# S'1c Pre-Registration: leakage-geometry reader extension (ladder branch (c))

Status: DRAFT v2 for freeze (2026-07-07). v1 failed a pre-freeze
adversarial verification (18 findings, 6 blockers); this version
incorporates every fix. Amendments after freeze require a new dated
section with a reason. Companion registration: S'1 Amendment d
(s_prime_1_middle_layer.md) extends the branch-(c) license to this
pipeline.

## Question

S'1 established: phi from the one-shot state-marginalized cone has no
predictive value (rho = +0.07, own CI includes 0); chain-level
additivity sits at the razor edge (median rel err 0.496, CI [0.41,
0.54]); closer-tactic responses are dominated by state-dependence
(1 - R^2: congr 0.94, norm_num 0.88, ring 0.76). Branch (c) asks: does
the reader M_J, extended along MEASURED leakage directions inside a
frozen capacity ball, recover predictive coker geometry — or is the
compressed dynamics memory-bearing in every practical chart — or
neither, returning the region to top-layer proposal?

## Formal frame (self-contained; external source vendored)

With J f = f o R (read through the chart), J* the chart-conditional
expectation, Pi = JJ*, Q = I - Pi, P_t the one-step proof-state
dynamics:

- LEAKAGE FORM D_t = (Q P_t J)*(Q P_t J): the Gram operator of what one
  step pushes outside the chart-measurable algebra. S'1's additivity
  error is its chain-scale estimate; per-tactic dispersion its diagonal.
- CONDITIONAL DRIFT CURVATURE V(z) = Cov(step response | z): the
  fiberwise second moment of the reader's blind spot.
- SCHUR VALUE of added features U: V_eff = V_RR - V_RU V_UU^+ V_UR;
  features are worth their held-out Schur reduction.
- ENTROPY-AWARE ACCEPTANCE: only walk-forward predictive value promotes
  a reader; in-sample leakage reduction never does (a reader must
  retain the progress current, not merely self-predict).
- BOREL SELF-ENCODING BAR: unconstrained measurable features trivialize
  every floor; all extensions live in the frozen capacity ball below.

External source: NS response-quotient program survey v0.9 + memo v0.10,
vendored at docs/external/ (SHA256SUMS pinned). All load-bearing
definitions are restated above; the vendored copies are context, not
normative references.

## Data reality (frozen constants derive from these measurements)

692 strict v3 kernel transitions across 544 chains; 395 distinct raw
tactic strings (321 singletons; 39 raw fibers with n >= 3 covering 301
rows; max raw fiber n = 41); 148 lag-1 linked transition pairs; 1,394
re-parsed S'0 fit-side rows (attempt-level, no per-step labels). All
per-fiber machinery is therefore registered at COARSE TACTIC-HEAD
granularity, never raw strings.

FIBER DEFINITION (frozen): the head token of the tactic step, mapped
into {intro, intros, apply, exact, rw, simp, norm_num, ring, linarith,
nlinarith, field_simp, have, cases, constructor, refine, omega, other}.
Minimum fiber size n_min = 8; below it a fiber is fit by hierarchical
shrinkage to the global model. DEGENERACY CLAUSE: a fiber's residual
enters the leakage Gram ONLY if its model beats the global-mean
predictor on held-out rows; failing fibers are excluded and their row
share disclosed (the realized_fallback lesson: no silent degeneracy).

COORDINATE HYGIENE (frozen, applied before any trace): the two exactly
duplicated coordinate pairs in the 34-dim defect vector
(audit.proof_size_risk == search.proof_term_growth_proxy;
search.constructor_branch_debt == carrier.constructor_branch_debt) are
deduplicated; near-deterministic carrier atoms are handled per
instrument 3.

## Frozen instruments

1. SWEEPING ANALYSIS (secondary frame, NOT gate-bearing). Sweep model:
   rank-1 bulk flow — per fiber class, the response component along the
   fit-population mean-response direction scaled by whitened ||D_before||
   (the response's own coordinates are never used as regressors). The
   co-moving residual feeds instruments 2-3 as the ESTIMATION frame.
   The GATE (instrument 5) runs in the Amendment-a frame unchanged —
   a gate-substrate change is not licensed by branch (c), and keeping
   the licensed frame doubles as the over-normalization control.
   MANDATORY DIAGNOSTIC: report the walk-forward rho of (i) the removed
   sweep component and (ii) raw-frame phi, descriptively; if the sweep
   component alone predicts u, that is reported as "the signal lives in
   the bulk flow" — a finding, not an artifact.
2. LEAKAGE GRAM ESTIMATION. On the kernel corpus at fiber-class
   granularity: registered model E[resp | fiber, z] = per-fiber ridge
   on whitened z (ridge lambda = 1.0 on whitened coordinates, frozen),
   with n_min/shrinkage/degeneracy per above; leakage = HELD-OUT
   residual covariance (5-fold by chain, never splitting a chain).
   S'0 fit-side rows enter ONLY as an attempt-level transfer check via
   script-summed predictions (the additivity-test convention) — they
   carry no per-step labels and never enter the fiberwise fit.
   Report: trace leakage share; top-5 eigendirections with
   principal-angle stability across folds; nearest extractable
   correlates. Published artifact: runs/s_prime_1c/leakage_spectrum.json
   (eigendirection loadings + correlates + coverage stats).
3. READER EXTENSION UNDER CAPACITY CONTROL. Candidate features, pinned
   to the ACTUAL payload schemas: (i) kernel-side head symbol of
   target_text after the frozen unwrapping rule (strip leading
   universal binders and negations, take the head constant);
   (ii) identifier-vocabulary indicators restricted to QUALIFIED
   CONSTANTS (dotted names; single-character binder names excluded)
   with corpus frequency >= f_min = 20; (iii) hypothesis-shape counts
   FIT-SIDE ONLY (kernel payloads carry no usable local context) —
   lane-asymmetric, disclosed, and excluded from any kernel-side
   selection statistic. Capacity: r_add <= 16 accepted dimensions.
   SELECTION CRITERION: held-out Schur reduction >= 30% of trace
   leakage, computed on the DEDUPLICATED coordinate set EXCLUDING
   carrier atoms that are deterministic functions of the candidate
   family (both numbers reported; the exclusion number gates), with the
   reduction spread over >= 3 eigendirections (no single direction may
   contribute > 50%). If the criterion is not met, instrument 5 DOES
   NOT FIRE and the branch-(c) gate license is PRESERVED (no extension
   worth testing = no shot spent); the leakage spectrum is still
   published.
4. MEMORY CONTROL — registered REOPENING of the branch-(b) question
   under a new same-corpus instrument (superseding, for this purpose
   only, the Amendment-b additivity rule). Comparison set: the 148
   lag-1 linked pairs ONLY, both arms fit and scored on it; capacity
   matched as effective degrees of freedom under the same ridge;
   previous-tactic enters at fiber-class granularity. VERDICT-BEARING
   only if the linked-pair count at analysis time is >= 120; below
   that, descriptive only — no NON-MARKOV or reader-coarseness
   diagnosis may bind either way (the corpus structure, 460/544
   single-transition chains, starves this instrument; the honest fix
   is longer verified chains from the D3 pool re-derivation).
   E-MZ RECONCILIATION: the standing "memory module killed by E-MZ"
   verdict is scoped to the loop-level memory cell; emz_memory.md's own
   resurrection clause requires a re-test when reader coordinates
   change — the kernel-granularity chart IS a coordinate change, and
   this instrument is registered as that re-test. A memory win here
   licenses ONLY a Gamma-chart-memory investigation under a fresh
   prereg; it does not resurrect the killed module.
5. GATE (single shot, Amendment-a frame). The extended reader
   recomputes phi_true (dual solve, whitened, RAW frame) and re-runs
   the corrected gate once: task-disjoint walk-forward; u defined
   exactly as in Amendment a (raw whitened norms); raced against
   ||D||; PASS requires rho_phi >= 0.10 with phi's own bootstrap CI
   excluding zero AND beating the baseline by >= 0.10 with CI
   excluding zero. EVIDENTIAL CLASS DOWNGRADE (disclosed): the
   score-side tasks are the same ~103 tasks whose per-task outcomes
   (gate_report.json) are on disk and were seen during S'1 analysis;
   freeze-time constants are design-bounded, not tuned, but a PASS on
   this reused score side is PROVISIONAL pending replication on
   unexposed waves (first S'3-era wave rows on tasks with no prior
   gate exposure). A FAIL is terminal for this branch.
6. FAILURE BRANCH. On gate failure (or an unmet Schur criterion
   followed by a decision not to extend), the region returns to
   TOP-LAYER PROPOSAL: the S'1 prereg's branch-(c) text governs — a
   second failure after extension ends middle-layer claims here. The
   published leakage spectrum is CANDIDATE DESIGN EVIDENCE for the
   S6/S'4 amendment that Rev 3 already obligates (not a registered
   conditioning signal; phi_true remains S'4's only registered signal
   and stays blocked), and the memory-control verdict is an input to
   any future Gamma rebuild prereg.

## Litmus (run before any real-corpus number is read; committed with
## the freeze)

Linear-Gaussian defect simulator with closed-form V, fixed-lag leakage,
and Schur residual; the closed-form expressions are committed AS CODE
with a derivation note beside the simulator (no external-document
dependency). Requirements: (i) the simulator resamples the EMPIRICAL
fiber-size distribution of the achieved corpus (395 fibers, median 1,
max 41), not a flat pool; (ii) per-quantity error metrics — relative
bias < 10% for scalar traces/shares, principal-angle tolerance <= 15
degrees for top-3 eigendirections on fibers above n_min; (iii) a
COLLINEARITY VARIANT where ground-truth signal is partially collinear
with the sweep direction, with a registered bound on signal loss under
instrument 1 (co-moving residual must retain >= 80% of the collinear
signal's walk-forward correlation in the raw frame); (iv) a degeneracy
variant where most fibers are singletons, verifying the degeneracy
clause excludes them rather than shipping zero residuals.

## Threats acknowledged in advance

- LANE BIAS: the kernel corpus lacks 45% of file-lane true successes;
  the leakage spectrum is conditional on the kernel-friendly tactic
  mix; the fit-side transfer check partially hedges.
- INTRO BINDER ARTIFACT: step-0 responses subtract kernel-lane
  after-defects from statement-derived root defects; intro-family rows
  register binder disappearance as payment because introduced
  hypotheses leave the extractor's view. Intro-family leakage is
  REPORTED STRATIFIED (separately from the pooled spectrum) and the
  artifact is disclosed wherever intro fibers appear in top
  eigendirections.
- Score-side reuse (instrument 5's downgrade clause) is the honest
  price of not having fresh waves; replication is registered as the
  promotion condition.
- Feature-direction overfit through the Schur selection remains
  possible within the capacity ball; the single-shot gate and the
  spread/cap rules are the controls.
- The memory control at lag 1 on 148 pairs bounds only lag-1 memory
  and only if verdict-bearing; longer memory is out of scope until
  longer verified chains exist.
- Capacity constants (n_min = 8, f_min = 20, r_add = 16, lambda = 1.0,
  30%, >= 3 directions, 50% cap, 120 pairs, 80% collinear retention)
  are design bounds frozen pre-outcome, not tuned values.
