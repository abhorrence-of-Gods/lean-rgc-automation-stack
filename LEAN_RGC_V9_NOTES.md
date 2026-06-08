# Lean-RGC v0.9 Notes

v0.9 moves the stack toward production-style pilot runs without requiring a
persistent Lean server yet.  The main additions are:

1. Focused two-phase exposure audit
   - `lean-rgc focused-audit` audits structural exposure prefixes separately
     from core tactics.
   - Outputs `exposure_audit.jsonl`, `frontier_tasks.jsonl`,
     `core_audit.jsonl`, and unified `responses.jsonl`.
   - This makes `intros`/simple split prefixes carrier exposure charts rather
     than primitive tactic labels.

2. Exposure frontier compatibility utilities
   - `frontier-audit`, `expose-frontier`, and `expose-frontiers` now have a
     compatibility implementation backed by audited or charted frontier tasks.
   - Frontier tasks carry the selected exposure prefix in `LeanTask.prefix`.

3. Dry-run exposure simulation
   - The dry-run executor now simulates intro exposure for forall/imp goals, so
     CI/Colab diagnostics reflect that `intros` exposes `n = n` before `rfl`.
   - Real Lean execution remains authoritative.

4. Multi-carrier matrix utilities
   - Build a carrier response matrix from audit rows.
   - Report uncovered carrier atoms and unsafe action fractions.
   - Annotate/filter actions with carrier-matrix safety.

5. IR-driven candidate compatibility
   - Existing `ir-candidates` and structured textual IR utilities are included
     in the v0.9 bundle for next-stage structured proof-state experiments.

Important status:
- v0.9 is still file-based.  It is suitable for 1k--10k audit pilots.
- Persistent Lean worker/server and true structured Lean goal extraction remain
  the next major production step.
- Premise retrieval is still lexical/chart-level, not semantic Mathlib retrieval.
