# G1 Pre-Registration: RFT-primary training vs frozen baseline (production)

Status: registered before the production G1 run. Thresholds frozen;
amendments require a new dated section with a reason.

Prior-exploration disclosure: a 40-task pilot (g1_rft_pilot, 2026-07-05)
ran the training loop end-to-end (solve 19->33/40 across 4 waves) WITHOUT a
control arm; its solve trajectory conflates training with error-feedback
repair and informs only feasibility/throughput, not effect size. All 40
pilot tasks lie INSIDE the evaluation set below, so the pilot's LoRA
weights are contaminated for evaluation and MUST NOT seed the production
run: training starts from the base model.

## Hypothesis

Under an identical generation protocol and per-theorem budget, the
RFT-primary (+ stratified-RLOO auxiliary) fine-tuned policy achieves a
higher paired solve rate than the frozen base policy on a held-out task
set. Mechanistic secondary claim: gains concentrate in the FLAKY stratum
(tasks with historical 0 < p <= 0.1), not the reliable one — reweighting
pass@k into pass@1, not sharpening of already-easy tasks.

## Task split (contamination rule)

- EVAL (frozen): the 130 miniF2F-test tasks of the pilot7 episode set.
- TRAIN: the 113 miniF2F-test tasks OUTSIDE the eval set (243 total;
  disjointness verified 2026-07-05). Optionally extended with the miniF2F
  valid split if fetched; any extension is recorded before the run.
- No task appears in both. The pilot7 a1 = 47.7% figure is CONTEXT only —
  the control arm is a fresh base-model evaluation under this protocol
  (the AWQ-server -> in-process NF4 policy change makes old absolute
  numbers non-comparable).

## Arms

- C (control): base Qwen2.5-7B-Instruct (prequantized bnb-4bit), no
  adapter.
- T (trained): same base + LoRA after N_train waves of run_grad_loop on
  the TRAIN set with difficulty-stratified RLOO (grad-loop --difficulty)
  and the three collapse guards (prerequisites below).

Both arms evaluated with the SAME in-process protocol: 8 attempts per
theorem, raw-Lean-error feedback between attempts (a1 protocol), fixed
decoding (temperature 0.2, top_p 0.95, max 512 new tokens), same seeds,
same Lean audit lane. Solve = any attempt verifies.

## Training configuration (frozen)

- GradInvariants defaults (NF4, LoRA r16/a32, G=8, batch>=8, checkpointing,
  KL hard gate 0.5/seq on RLOO).
- Difficulty table: recomputed from the run's OWN accumulated wave rows
  after each wave (grad-difficulty semantics, shrinkage 20; wave 0 runs
  unstratified). No pilot-derived difficulty enters training (train tasks
  have no pilot history; eval-task history is never used in training).
- N_train = 8 waves (sized from measured pilot throughput ~30 min / 4
  waves / 40 tasks; expected ~4-6 h on the RTX 4090 pod). Checkpoint after
  every wave; the evaluated T is the LAST checkpoint (no post-hoc
  checkpoint selection).
- Supply planning constants: 25-48% of tasks yield >=1 verified trace per
  wave (measured band), degenerate groups 52-67%.

## Prerequisites (blockers; must land before launch)

1. RFT trace dedup per (task_id, tactic) within a wave + per-task cap of 2
   traces/wave (empirical duplication 3.2x; M1: 93% residual-state dup).
2. A drift guard on the RFT path (KL-to-base term or entropy floor) — the
   KL gate currently covers only RLOO.
3. Per-wave trace-concentration logging (top-k share of traces by task)
   in grad_run.jsonl as the collapse early-warning gauge.
4. An eval-mode driver: budget-8 feedback loop through RolloutEngine
   generation with NO training step, emitting episode rows compatible with
   the paired bootstrap report.

## Primary endpoint

Paired solve-rate delta T - C over the 130 eval tasks, 10,000-resample
paired bootstrap, seed 0. Decision: the training thesis is supported iff
the 95% CI excludes zero in favor of T. Detection floor at n=130 is
~7.7-10.8pt; a true effect below that is not resolvable here.

## Secondary endpoints (reported, not gating)

- Stratum deltas using pilot7 pooled per-task p on EVAL tasks:
  p=0 stratum / flaky (0<p<=0.1) / reliable (p>0.1). Support pattern =
  flaky-dominant gains; easy-sharpening signature = reliable-only gains
  (triggers the entropy/dedup review before any follow-up run).
- Degenerate-group fraction and RLOO advantage mass per wave (stratified
  vs the 62-67% task-grouped band).
- Trace concentration (Gini / top-10% share) per wave.
- Measured throughput and VRAM (replacing the remaining projections).
- Offline twist shadow calibration: rerun the D1 pipeline on this run's
  archived wave rows (R0e collector) — no runtime hook needed.

## Pre-declared null/negative branches

- CI includes zero and point estimate < +2pt: the RFT-primary mechanism is
  not supported at 7B under this budget; the roadmap pivot is search-side
  (twist-budgeted eval, verified-prefix salvage) per the standing cost
  analysis — not more waves of the same.
- CI includes zero and point estimate in [+2pt, floor): power-limited;
  extend EVAL with the 113 train-disjoint valid-split tasks (if fetched)
  in a dated amendment BEFORE unblinding any extension data.
- Positive but reliable-stratum-only: mechanism is easy-sharpening;
  mitigations (dedup cap tightening, entropy floor) become mandatory
  before any scale-up claim.

## Results 2026-07-05 (registered execution)

Training (113 disjoint tasks, 8 waves, online-stratified RLOO, all four
collapse guards active): 90/113 solved during training; RFT-KL drift
bounded (peak 3.77 nats/seq at wave 1, decaying); trace concentration
flat (gini <= 0.17); 2,769 wave rows archived. Artifacts:
runs/g1_prod_train/. Eval arms: in-process protocol, 8 attempts,
raw-error feedback, temperature 0.2, seed-paired; T = wave_7 checkpoint.

- PRIMARY: C = 35/130 (26.9%), T = 52/130 (40.0%).
  Paired delta T - C = +13.1pt, 95% bootstrap CI [+6.2, +20.0]
  (10,000 resamples, seed 0). The CI excludes zero in favor of T:
  THE TRAINING THESIS IS SUPPORTED. The point estimate also clears the
  7.7-10.8pt single-gate detection floor.
- MECHANISM (stratum deltas, pilot7 pooled p labels): flaky +15.8pt
  (n=57), p0 +12.5pt (n=32), reliable +5.7pt (n=35), no-history +33pt
  (n=6). FLAKY-DOMINANT: the registered pass@k->pass@1 reweighting
  mechanism is supported; the easy-sharpening signature (reliable-only
  gains) did not appear. Note the p0 stratum also moved — under the
  in-process protocol some pilot-p0 tasks are reachable, so the stratum
  labels (measured under the old AWQ protocol) are noisy as
  acknowledged.
- First-solve curves (cumulative by attempt): C [11,22,26,28,30,32,33,
  35] vs T [13,33,41,45,48,50,52,52]. T separates hardest at attempt 2
  (33 vs 22) — the trained policy gains BOTH on first proposals and,
  most strongly, on the first error-feedback response, consistent with
  the registered threat note that eval gains can include error-response
  behavior; reported, as promised, so readers can see the split.
- Context: pilot7 a1 47.7% is not comparable (different serving stack
  and prompt contract); the paired in-process design was registered for
  exactly this reason.

Decision per the frozen rules: supported branch. Next steps that this
result licenses: scale-up planning may proceed, subject to the
registered caveats (single seed, miniF2F-internal transfer only).

## Amendment 2026-07-05c: RESULT INVALIDATED BY LABEL DEFECT (supersedes the Results section)

The S1 stepwise replay (exact kernel re-audit of claimed successes)
exposed a storage-time classifier hole: _ERROR_RE missed tagged Lean
diagnostics ('error(tag):'), mis-keying them into neighboring blocks —
a block whose ONLY errors were tagged carried no messages and was
classified SUCCESS. Training then reinforced tagged-error-failing
scripts (Lean3-isms such as 'eq.mp', 'int.add_comm'): reward hacking
through the label hole, i.e., the arbiter itself was gameable — the
exact Goodhart class this program's design warns about, one level
deeper than anticipated.

Corrected recount (label_audit, chunk-wide re-attribution against each
row's own R0c block range; lower bound — tagged errors with no
preceding plain error anywhere were dropped at storage):
- Eval C: 36 success rows -> 12 false; corrected 23/130.
- Eval T: 53 -> 24 false; corrected 28/130.
- CORRECTED PRIMARY: delta = +3.85pt, 95% CI [-0.77, +8.46] — does NOT
  exclude zero. THE SUPPORTED VERDICT IS RETRACTED.
- Training: 71/144 success rows false — roughly half the RFT gradient
  signal was garbage; the wave_7 checkpoint, the twist-v2 artifact and
  the difficulty table trained on these labels are QUARANTINED.
- Ground truth: 5/5 sampled false successes re-audited through the
  fixed pipeline (tagged-aware _ERROR_RE) now classify elab_error/fail.

Under the corrected point estimate (+3.85pt in [+2pt, floor)) the
pre-declared power-limited branch would apply, but the deeper defect —
corrupted training labels — dominates: the honest disposition is
INVALIDATED PENDING RE-RUN with the fixed classifier end to end
(training labels, eval labels, and the RFT trace filter). Collateral to
re-examine: D1 gates used pilot labels with the same hole (retro
recount via the D3 chunk reconstruction is possible); M1 (partial rows)
and D3 (error positions, not success labels) are unaffected.

## Amendment 2026-07-05d: G1re — registered re-run with the fixed classifier

Registered BEFORE the re-run starts. Protocol identical to the original
execution (113 train / 130 eval split, 8 waves, online-stratified RLOO,
collapse guards, in-process paired eval at 8 attempts / temp 0.2 /
seed 0, 10k paired bootstrap), with exactly these differences:
1. Classifier fix a681bd1 active end to end (training labels, RFT trace
   filter, eval labels): tagged diagnostics now attribute to their own
   blocks.
2. Fresh LoRA init (the quarantined wave_7 checkpoint must not seed).
3. Post-hoc label-audit CANARY GATE: label_audit.recount_run over every
   produced run dir must find < 1% false-success rows; a violation halts
   analysis and reopens the classifier investigation before any endpoint
   is read.
Primary endpoint, strata, curves, and null branches: unchanged from the
original registration. The corrected-label +3.85pt from amendment c is
the prior expectation, NOT a threshold.

## Amendment 2026-07-05e: authoritative labels; defects #3/#4; G1re restarted

The isolated (batch_size=1) re-audit of all 394 claimed-success pairs is
the authoritative label source (run-to-run reproducibility 21/21).
Results: pilot 25/214 pairs true, g1_train 6/120, g1_evalC 2/30,
g1_evalT 0/30. AUTHORITATIVE G1: C = 5/130, T = 4/130, delta = -0.77pt,
CI [-2.3, +0.0] — nothing remains of the original effect.

Two further storage-time defects were identified while validating the
correction instrument:
- Defect #3 (chunk poisoning): a dangling construct in the last block
  errors past all block ranges; the global message failed every block
  in the chunk (false failures).
- Defect #4 (syntax bleed): a block ending in an incomplete construct
  (e.g. bare `calc`) absorbs the NEXT block's source; the parse error
  lands in the neighbor's range (false failure) while the offender
  carries no error (false success) — undetectable from stored rows.
Both fixed at source by the ownership attribution rule (commit 6d24fe9).
The first G1re attempt trained under defect #4 and was aborted; G1re2
relaunched fresh with all fixes active. The label-audit canary gate of
amendment d still applies, PLUS a new gate: an isolated re-audit of a
random sample of >= 30 claimed successes from the G1re2 run must agree
with the stored labels at >= 95%.

## Threats to validity acknowledged in advance


- miniF2F is likely in the base model's training data; the paired design
  absorbs this for the delta, but absolute rates are not generalization
  claims.
- Train and eval share the miniF2F distribution; transfer beyond miniF2F
  is out of scope for G1.
- Single 24GB GPU: no seed replicates; seed variance is unquantified and
  acknowledged (one seed, fixed in advance: 0).
- The feedback loop inside evaluation means T's gains can include better
  ERROR-RESPONSE behavior, not just better first proposals; the per-attempt
  solve curve (attempt index of first solve) is reported to expose this.
