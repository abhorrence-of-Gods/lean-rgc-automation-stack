# Lean-RGC v41: Arithmetic Teacher Graph

This release adds a first implementation of arithmetic teacher constraints as goal-state transformation charts.

The key shift is from treating arithmetic as a data curriculum to treating arithmetic identities as partial structure-preserving transformations on `StructuredProofState` rows:

```text
g --tau_I--> tau_I(g)
```

The implementation is deliberately conservative.  Transformations are currently target-expression text/kernel-chart rewrites with a schema designed to be replaced by true kernel Expr rewrite audits.  All generated rows are witness/chart artifacts, not canonical observables.

## Commands

```bash
lean-rgc arithmetic-teacher-graph \
  --structured-states runs/round_00/audit/structured_states.jsonl \
  --out runs/round_00/arithmetic_teacher
```

Outputs:

- `arithmetic_teacher_identities.jsonl`
- `arithmetic_teacher_transformations.jsonl`
- `arithmetic_teacher_audits.jsonl`
- `arithmetic_teacher_constraints.jsonl`
- `arithmetic_teacher_actions.jsonl`
- `arithmetic_teacher_report.json`

A chart-level audit can also be run:

```bash
lean-rgc arithmetic-teacher-audit \
  --transformations runs/round_00/arithmetic_teacher/arithmetic_teacher_transformations.jsonl \
  --structured-states runs/round_00/audit/structured_states.jsonl \
  --out-rows runs/round_00/arithmetic_teacher/arithmetic_teacher_audit_rows.jsonl \
  --report-out runs/round_00/arithmetic_teacher/arithmetic_teacher_audit_report.json
```

## Status

`ArithmeticTeacherGraph` rows are `goal_state_transform_chart_not_canonical`.  They become POMS-relevant only after kernel transition audit, response/carrier invariance checks, and least-repair evidence.
