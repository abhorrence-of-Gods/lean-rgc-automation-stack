# Lean-RGC v13: qgen loop integration

This revision wires the coker-driven generator (`qgen`) into the round-based
pipeline and iteration loop.

## What changed

- `pipeline --qgen` now runs qgen after the base audit and writes a `qgen/`
  artifact directory inside the pipeline run.
- `qgen` now writes `qgen_accepted_actions.jsonl` in addition to the full
  candidate and acceptance tables.
- `iterate --qgen --qgen-merge-actions` now merges accepted qgen actions into
  the next round's action universe.
- `rgc-loop --qgen --qgen-merge-actions` also picks up accepted qgen actions.
- Iteration summaries now expose qgen counts: proposed contexts, accepted
  contexts, defect proposals, carrier-incidence proposals, and failure charts.

## Artifact contract

`pipeline --qgen` creates:

- `qgen/qgen_report.json`
- `qgen/qgen_defect_atoms.jsonl`
- `qgen/qgen_defect_registry.json`
- `qgen/qgen_context_candidates.jsonl`
- `qgen/qgen_context_acceptance.jsonl`
- `qgen/qgen_accepted_actions.jsonl`
- `qgen/qgen_carrier_incidence.jsonl`
- `qgen/qgen_failure_signatures.jsonl`

Only `qgen_accepted_actions.jsonl` is intended for automatic merging into the
next round. The full candidate file is retained as a chart/audit artifact.

## Canonical status

All qgen outputs remain candidate charts/witnesses. They are not canonical
proof objects. Promotion still requires the POMS conditions: parent obstruction
non-payment, dual evidence, and least repair.

## Example

```bash
lean-rgc iterate \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/qgen_loop \
  --rounds 2 \
  --dry-run \
  --qgen \
  --qgen-merge-actions \
  --next-action-cap 128
```

For conservative runs, keep the default qgen margin threshold. For exploratory
chart expansion, lower it:

```bash
--qgen-margin-threshold -1.0
```
