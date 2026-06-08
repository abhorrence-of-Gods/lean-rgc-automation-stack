# Lean-RGC v0.10 Notes

This version tightens the self-improving loop around focused frontier exposure and structured IR candidates.

## Additions

- `iterate` now supports frontier normalization, bulk audit mode, IR candidate generation, optional IR candidate audit, and IR coker acceptance.
- Pipeline can audit IR-driven candidates and accept them with the same finite coker-margin proxy used for registry-generated candidates.
- Iteration feedback now prefers accepted IR actions over raw IR candidate charts when constructing the next-round action universe.
- Response learner is more robust to synthetic/legacy response rows that contain a `response` dict but lack explicit `response_keys`.

## Intended use

```bash
lean-rgc iterate \
  --tasks runs/corebench_tasks.jsonl \
  --out runs/v10_iter \
  --rounds 2 \
  --dry-run \
  --jobs 4 \
  --candidate-mode state \
  --frontier-normalize \
  --ir-candidates \
  --audit-ir-candidates \
  --ir-accept-coker \
  --fit-gamma
```

For real Lean runs, add `--lean-cmd "lake env lean" --workdir /path/to/lake/project --import-mode core|mathlib`.

## Status

Still file-based, not a persistent Lean server.  Structured IR is still textual/heuristic, but now it participates in the audit/accept/iterate loop rather than remaining a side chart.
