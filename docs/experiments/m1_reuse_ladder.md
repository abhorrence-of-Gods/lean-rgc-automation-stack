# M1 Pre-Registration: Reuse-rate ladder over cache-key gauges

Status: registered before the analysis has been executed. Thresholds frozen;
amendments require a new dated section with a reason.

## Question

Does the central layer of the factor-bridge program (confluence, transfer,
accumulation between and within theorems) have a substrate at all? The
"zero inter-theorem reuse at state_hash_norm" observation that motivated
skepticism was made at smoke scale (48 transitions, 29 dry_run) plus design
reasoning — it has never been measured at pilot scale. M1 measures reuse as
a function of the KEY GAUGE, from raw strings down to a minimal-support
approximation, pricing the bet before any cache is built.

## Data and unit

All status == "partial" rows in the pilot tarball
(`runs/vast_transitions/pilot_waves_backup.tar.gz`, ~4,522 expected): the
only rows whose `after_state.goals_text` carries genuine residual goal
states. Unit of analysis: one parsed goal block (hypotheses, target) as
split by `lean_rgc.lean.state_parser.LeanMessageParser` (usable only since
the 2026-07-05 mojibake fix). Rows whose text yields zero parsed goals are
excluded and counted.

## Key ladder (gauges)

- K0 raw: stripped raw goal block text.
- K1 text-alpha: hypothesis names renamed v0..vn in order of appearance
  (occurrences rewritten in types and target), hypotheses sorted by
  canonical type. TEXT-LEVEL APPROXIMATION of alpha-canonicalization —
  the exact rung needs kernel data (M2, rides on R8).
- K2 goal-only: canonical target alone (variables renamed in
  target-appearance order); context ignored.
- K3 goal + support proxy: canonical target plus the sorted canonical
  types of the target's hypothesis dependency closure (names occurring in
  the target, then names occurring in those hypotheses' types,
  transitively). Proxy for proof-term minimal support — the true support
  needs proof terms (M2). Directional errors acknowledged: dependency
  closure UNDERCOUNTS support used only through automation (simp) and is
  a lower bound on any true support.

## Columns

- Within-theorem: duplicate rate = 1 - (unique keys / instances), pooled
  over tasks (same task_id, across runs, waves, proposals).
- Inter-theorem: fraction of instances whose key also occurs under at
  least one other task_id.
- Squeeze check (difficulty stratification of inter-theorem hits): an
  inter-theorem hit is TRIVIAL-LOOKING if its canonical target is
  numeric-only (tokens drawn from digits and + - * / ^ = ( ) < > le/lt
  symbols), reflexive (lhs == rhs around a top-level =), or the literal
  True. Non-trivial inter-theorem rate is reported separately: hits that
  are trivial-looking sit in territory mathlib/simp already covers, so
  they do not evidence the accumulation bet.

## Frozen decision rule

Evaluated at K3 (the best gauge measurable without proof terms):

- inter-theorem rate < 1% AND within-theorem duplicate rate < 10%
  -> "central layer degenerates": plan the middle layer as within-theorem
  twisted SMC only; accumulation moves to offline lemma extraction; the
  cache design (subsumption keys) is deprioritized until M2 contradicts.
- Otherwise -> "central layer live": specify the subsumption cache
  (goal + minimal support keys hardened by proof-term certificates) as a
  v98+ deliverable, and add the M2 riders (support extraction,
  mvar-closure certification) as mandatory R8 cargo.

Secondary readouts (reported, not gating): the full rung-by-rung ladder
(where does the entropy live), per-wave breakdown, and the trivial fraction
of inter-theorem hits (squeeze evidence).

## Results 2026-07-05 (registered analysis, first execution)

Report: `runs/m1_reuse_ladder/report.json`. Extraction: 4,522/4,522 partial
rows parsed (zero failures; enabled by the same-day state_parser fixes:
mojibake turnstile, subscripted/multi-binder hypothesis lines), 4,536 goal
instances across 114 tasks.

Ladder (within-theorem dup rate / inter-theorem rate):

- K0 raw:          75.3% / 0.0%
- K1 text-alpha:   92.4% / 1.04%
- K2 goal-only:    93.1% / 1.12%
- K3 goal+support: 93.1% / 1.04%

DECISION (frozen rule): central_layer_live — the within-theorem arm passes
overwhelmingly (93.1% >= 10%; secondary readout: 69.8% even restricted to a
single (task, run), so confluence is not a cross-run artifact).

Honest inspection amendment (same day, before any downstream use): the
squeeze_check's automated trivial_fraction read 0.0, but manual inspection
of ALL shared K3 keys shows the automated proxy has false negatives. The
inter-theorem hits are exactly three key groups: `⊢ ∀ (x : ℝ), True`
(39 instances — forall-wrapped True, trivial, missed by the proxy) and
`⊢ ?m.46` / `⊢ ?m.32` (8 instances — bare unassigned metavariable targets,
elaboration artifacts whose numeric coincidence across tasks is
meaningless). Corrected reading: NON-TRIVIAL inter-theorem reuse at the
text gauge is ~0%. The squeeze prediction is CONFIRMED, not refuted.

Consequences:
- Within-theorem transposition value is real and large (a ~13x key
  compression: 4,536 instances -> 341 unique K1 keys): residual-state
  dedup for repair prompting, RFT trace dedup, and twist sharing are
  licensed as within-theorem machinery.
- Inter-theorem accumulation does NOT live at the residual-state text
  gauge. If it lives anywhere, it is at the kernel/lemma gauge — M2
  (proof-term support extraction + mvar-closure certification on
  kernel_rpc, R8 cargo) remains the decisive measurement, and offline
  lemma distillation remains the accumulation route.
- Proxy fix for any rerun: extend is_trivial_target to strip binder
  prefixes and to treat bare-metavariable targets as degenerate (excluded,
  not merely trivial).

## Threats to validity acknowledged in advance

- Text-level canonicalization is approximate; K1-K3 rates are lower bounds
  on what kernel-level canonicalization could achieve (misses definitional
  equality entirely).
- Residual goals of FAILED whole-script attempts are a biased sample of
  reachable states (they sit downstream of wrong scripts); within-theorem
  confluence measured here reflects the deployed wavefront loop, not tree
  search.
- Constants are not abstracted: inter-theorem hits require literally
  shared constants after variable renaming. This biases against
  inter-theorem reuse; M2's kernel-level and lemma-gauge measurements can
  only raise it.
- The 3.2x duplication of successful (task, tactic) pairs already proves
  script-level within-theorem confluence exists; M1 asks the finer
  question at residual-state granularity.
