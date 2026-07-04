# D1 Pre-Registration: Retroactive Twist Gate (FPR of pre-audit pruning factors)

Status: registered before the registered analysis has been executed. The
thresholds below must not be edited after the first report is generated;
amendments require a new dated section with a reason.

Prior-exploration disclosure: during the 2026-07-05 feasibility audit, a crude
prototype (first-tactic-token frequency factor, shrinkage 20, task-grouped
5-fold CV) was run on the same rows and observed mean score 0.142 on
successes vs 0.057 on failures, and tau=0.02 -> FN 3.5% / 28% call savings.
The criteria below were chosen with that prior knowledge and are therefore
biased toward passing C2 for the token arm; C1, C3, C4 and all set-level
endpoints were not explored before registration.

## Question

Can a cheap pre-audit factor h_hat(s, a) — measurable before any Lean call —
prune candidate proposals with a bounded false-negative rate on actually
successful candidates? This is the go/no-go for every "twist" use downstream
(eval-harness candidate budgeting, shadow calibration in GPU runs,
difficulty stratification). Deployment note registered in advance: the
adversarial verification of 2026-07-05 refuted wall-clock pruning inside the
grad loop (Lean phase is 5-14% of wave time; pruning destroys RFT positive
supply), so a PASS here does NOT license a grad-loop pre-audit pruner; it
licenses (i) eval-harness budget reallocation, (ii) shadow-mode calibration,
(iii) stratification inputs.

## Data

`runs/vast_transitions/pilot_waves_backup.tar.gz`: all `*/wave_*/
micro_audit.jsonl` rows (11,189 expected). Label: primary y=1 iff
status == "success", all other statuses 0. Sensitivity arm: rows with
status == "partial" excluded. Unit of pruning: candidate row; unit of
set-level analysis: (run, wave, boundary_id) candidate set.

## Arms (identical estimator class per arm: naive-Bayes log-lift with
count shrinkage 20, isotonic-calibrated on training folds)

- T (token): first tactic token only.
- F (factorized): T + binarized defect_before coordinates (carrier.* > 0
  flags, goal.*/type.*/search.* quantized) — the FactorizedTwist-lite over
  the existing 34-dim reader.
- R (raw signal): hashed token bag of tactic text + boundary feedback_text
  (E1 lesson: every finitization must race the raw signal).
- FR: union of F and R features (sizes the text port).

## Protocol

Task-grouped 5-fold CV (a task_id never spans train/test). All reported
scores are out-of-fold. Bootstrap CIs: 1,000 resamples clustered by
prompt_hash (cross-arm cache reuse makes candidate sets sharing a prompt
non-independent). Seed 0 everywhere.

## Frozen criteria

- C1 (discrimination): out-of-fold AUC(F) >= 0.70.
- C2 (admissible pruning value): exists tau with candidate-level
  FN(tau) <= 5% and call savings (fraction pruned) >= 20%.
  Set-level endpoint reported at B_survive in {1,2,3}: fraction of
  positive sets whose successes are all pruned.
- C3 (calibration): ECE <= 0.05 on out-of-fold isotonic-calibrated F scores
  (10 equal-count bins).
- C4 (raw-signal race): AUC(R) - AUC(F) <= 0.02. If violated, the
  factorized reader is losing signal again (E1 pattern): a text port is
  REQUIRED in any deployed twist, and the G3 renderer bet is resized
  accordingly.

## Decisions

- C1 and C2 pass -> twist cleared for eval-harness budgeting + shadow mode
  in the next GPU run (D2-as-revised).
- C3 pass -> state_value (marginalized) head cleared as RLOO baseline input
  once stratified grouping lands.
- C1 fail -> the factorized-twist limb is sealed; v99 shrinks to G4; only
  raw-signal scoring remains a candidate.
- C4 fail -> text port mandatory before any deployment; record as direct
  sizing input for the G3 renderer decision.

## Threats to validity acknowledged in advance

- Rows are whole-proof repair proposals, not tactic steps: measured FPR is
  for pruning LLM whole-script proposals, not a step-level psi_trans.
- defect_before is constant within a candidate set (root state each wave),
  so within-set ranking comes from tactic/text features only.
- 680 success rows / ~429 positive sets bound the precision of low-FN
  estimates; CIs must be reported next to every gate number.
- Pilot proposals came from Qwen2.5-7B-AWQ at temp 0.7; transfer to other
  generators is not claimed.
