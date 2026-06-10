# Lean-RGC v0.5 Notes

This release adds the first implementation of Focused Carrier Exposure and automatic defect mining.

## New

- `GoalShapeParser` / `goal-shapes` command for coarse proof-state shape charts.
- `StateDependentCandidateGenerator` focused exposure path is now the default state candidate route.
- Structural exposure prefixes such as `intros` and `constructor` are stored in action metadata as prefix/core decompositions.
- `mine-defects` now records an observed defect registry from micro-audit / response rows.
- `auto-defects` applies a mined registry to task/state rows.
- `pipeline --mine-defects` writes `defect_registry.json` and score rows.
- `batch-audit` response rows now include `task_id` and full `action` metadata, enabling atom mining and quotient discovery by generated tactic decomposition.

## Design

`intro` and similar structural tactics are treated as carrier-exposure contexts, not primitive learned tactic labels.  This follows the Lean-RGC / CanObsNS rule: raw labels and proof witnesses are charts; response quotient and carrier quotient are the primitive objects.

## Suggested first run

```bash
lean-rgc pipeline \
  --tasks examples/core_theorems.jsonl \
  --out runs/v5_core \
  --dry-run \
  --candidate-mode state \
  --max-actions 24 \
  --mine-defects \
  --fit-gamma
```

For real Lean mode, add `--lean-cmd "lake env lean" --workdir /path/to/lake/project --import-mode core`.
