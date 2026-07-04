# E-MZ Pre-Registration: Mori-Zwanzig memory test on wave chains

Status: registered before the analysis has been executed. Thresholds frozen;
amendments require a new dated section with a reason.

## Question

Does the finite reader's coordinate stream carry usable memory beyond the
current wave — i.e., is the deployed closed loop approximately Markov in the
reader coordinates? Mori-Zwanzig guarantees that ANY coarse-graining induces
a memory kernel; the question is whether its magnitude, at the deployed
reader, is large enough to justify building a learned memory module
(v98 memory.py LoopMemoryCell) at all. This test decides that module's
existence before a line of it is written.

## Data

Wave chains from `runs/vast_transitions/pilot_waves_backup.tar.gz`: for each
(run dir, task_id), the sequence over waves of that task's candidate-set
outcome summaries. Transition sample at position t: features of waves t and
t-1 predict the outcome at wave t+1 (so chains of length >= 3 contribute;
the no-lag baseline is evaluated on the SAME transitions for comparability).

- Outcome: any success in the wave t+1 candidate set.
- Wave features f_t: candidate count, status counts, mean defect_after
  (34-dim), mean response (34-dim) — the typed aggregate; and a hashed token
  bag of wave-t Lean messages — the text aggregate.
- wave_index is included as a feature in ALL arms so lag features cannot
  win merely by encoding position.

## Arms

- L34: typed aggregates only; lag test = [f_t] vs [f_t, f_{t-1}].
- LTXT: message token bag only; same lag test.
- BOTH: union.
- T2: [f_t, f_{t-1}] vs [f_t, f_{t-1}, f_{t-2}] on chains of length 4.

Estimator: L2-regularized logistic regression (numpy IRLS), task-grouped
5-fold CV, out-of-fold AUC. Delta-AUC = AUC(with lag) - AUC(without).
Permutation null: permute the lag block across transitions within
(wave_index) strata, 200 permutations, seed 0; p = fraction of null
Delta-AUC >= observed.

## Frozen decision thresholds (v98 memory.py existence)

- Delta-AUC(L34) < 0.01 or p > 0.1 -> KILL memory.py. The reader is
  approximately Markov for loop purposes; v98 ships renderer-only.
- 0.01 <= Delta-AUC(L34) < 0.03 -> minimal EMA port (exponential average of
  past defect aggregates appended to the renderer input, one virtual token,
  no learned recurrence).
- Delta-AUC(L34) >= 0.03 -> learned memory justified; if T2 adds again on
  top, a GRU; if only t-1 matters, a linear one-lag port.
- If Delta-AUC(LTXT) passes a threshold that Delta-AUC(L34) fails, the
  memory lives in signal the 34-dim reader DROPS (Mori-Zwanzig unresolved
  variables; E1 pattern): a raw-text port precedes any memory cell, and
  v98's internal order becomes renderer-with-text-port first.

## Threats to validity acknowledged in advance

- Chains exist only where earlier waves failed (failure conditioning);
  results describe the deployed repair loop's kernel, which is the object
  the memory cell would model, but not an unconditioned proof process.
- n (transitions) is in the hundreds; small Delta-AUC below ~1pt is not
  resolvable — which is exactly why 1pt is the kill line.
- If the reader coordinates change (e.g., G3 renderer), this test must be
  rerun on new wave chains before resurrecting a killed memory module.
