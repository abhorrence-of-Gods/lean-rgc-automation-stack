# Toy 0: Phase-HMM Closed Loop (v95)

Exactly solvable validation stage for the phase-split / certified-freezing
theory, run BEFORE the gradient pipeline (`lean_rgc/grad/`, v96+) spends GPU
budget on it. Tokens are meaningless permuted labels; the only structure is
the future law and the closed-loop kernel. Module:
`lean_rgc/toys/phase_hmm.py`; tests: `tests/test_v95_phase_hmm_toy.py`;
report: `run_toy0_report()`.

## Validated hypotheses (all exact unless noted)

- **H1** Phases are recoverable as future-law equivalence classes without
  any semantics: in scenario S1 the within-pair token preference difference
  gives `g_future = 0.293` while reward and loop kernel are *exactly* equal.
- **H2** Splitting must be driven by the loop, not the future law: S1's
  A-cell does NOT split (`g_loop = g_target = 0` exactly, machine zero),
  S2's A-cell splits (`g_loop = 0.175`, `g_target = 0.154`), S2's B-cell —
  future-different but loop-identical — is correctly rejected at ~1e-17.
- **H3** Hierarchical splitting beats flat clustering at equal per-leaf
  budget purely through look structure (2 in-family tests at z=2.0 vs 6
  Bonferroni-corrected pairwise tests): recovery 0.45 vs 0.325 on the hard
  scenario S2h (sampled, seed-fixed).
- **H4** Freezing requires the margin rule, not just entropy reduction:
  identical margin (0.30) is rejected at n=2 (threshold 0.477) and accepted
  at n=200 (threshold 0.048), choosing the correct child.

Additional exact measurements: loop effect (closed − open) = +0.036;
selection defect 0.0 (S1) vs 0.35 (S2) — dropping the phase from the finite
reader is only safe when the phase is loop-irrelevant; dual error
(init-coordinate vs phase-ensemble prediction) shrinks 15× when the atlas is
refined to the true cell.

## Corrections folded into the grad roadmap (from design review)

1. **G3 gains a fourth arm**: the 34-dim typed vector rendered through a
   hand-written natural-language template (no learning, paid-index
   transport). Distinguishes transport failure (ε) from compression failure
   (δ) when the NeuralRenderer loses.
2. **prefix_bank gets a minimal split rule** (v97): a prefix whose
   downstream statistics are bimodal splits into two bank entries, using the
   same gain-vs-cost decision validated here; freezing alone is half of the
   pair this toy validates.
3. **Measured smoke before G1**: the memory/throughput numbers
   (batch ≥ 8 load-bearing, checkpointing mandatory) are logged as
   measurements in a 30-minute smoke, not asserted from analysis.

Version note: v95 = this toy stage; the grad skeleton shifts to v96+.
