# Lean-RGC v13: QGEN-in-the-loop iteration

This revision connects quotient-first generation (QGEN) to the iterative pipeline.

## What changed

- `lean-rgc pipeline --qgen` already produces finite coker-driven chart candidates:
  - `qgen/qgen_report.json`
  - `qgen/qgen_defect_atoms.jsonl`
  - `qgen/qgen_defect_registry.json`
  - `qgen/qgen_context_candidates.jsonl`
  - `qgen/qgen_accepted_actions.jsonl`
  - `qgen/qgen_carrier_incidence.jsonl`
  - `qgen/qgen_failure_signatures.jsonl`
- `lean-rgc iterate --qgen` now runs the QGEN stage inside each round via the pipeline.
- `lean-rgc iterate --qgen --qgen-merge-actions` merges QGEN accepted actions into the next round's action universe.
- Round summaries now include QGEN counts:
  - `qgen_contexts`
  - `qgen_accepted`
  - `qgen_defects`
  - `qgen_carriers`
  - `qgen_failures`

## Status

QGEN outputs are still candidate charts / witnesses. They are not canonical observables. Promotion still requires the POMS condition: parent non-payment, dual failure evidence, and least repair.

## Example

```bash
lean-rgc iterate \
  --tasks examples/core_theorems.jsonl \
  --out runs/qgen_iter \
  --rounds 2 \
  --dry-run \
  --import-mode core \
  --qgen \
  --qgen-merge-actions \
  --qgen-top-contexts 32
```
