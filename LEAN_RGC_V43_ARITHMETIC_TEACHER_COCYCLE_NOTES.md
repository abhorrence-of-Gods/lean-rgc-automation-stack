# Lean-RGC v43: Arithmetic Teacher Cocycle Audit Loop

v43 connects arithmetic teacher transition audits to a finite cocycle audit layer.

The goal is to move from arithmetic identities as rewrite-chart seeds to arithmetic identities as
multiplicative constraints on goal-state response dynamics:

\[
\Gamma_{J\circ I}\approx \Gamma_J\Gamma_I,
\qquad
b_{J\circ I}\approx \Gamma_J b_I+b_J.
\]

The implementation is still a finite audit chart, not a canonical teacher quotient. Canonical
promotion still requires parent non-payment, a dual certificate, and least repair evidence.

## New CLI

Build transition geometry directly from kernel transition audit rows:

```bash
lean-rgc arithmetic-teacher-transition-geometry \
  --kernel-audit-rows runs/round_00/arithmetic_teacher/kernel_transition_audit/arithmetic_teacher_kernel_audit_rows.jsonl \
  --out runs/round_00/arithmetic_teacher/cocycle_audit/arithmetic_teacher_transition_geometry.jsonl \
  --summary-out runs/round_00/arithmetic_teacher/cocycle_audit/arithmetic_teacher_transition_geometry_report.json
```

Audit finite cocycles using explicit composition rows:

```bash
lean-rgc arithmetic-teacher-cocycle-audit \
  --transition-geometry runs/round_00/arithmetic_teacher/cocycle_audit/arithmetic_teacher_transition_geometry.jsonl \
  --compositions compositions.jsonl \
  --out runs/round_00/arithmetic_teacher/cocycle_audit/arithmetic_teacher_cocycle_rows.jsonl \
  --summary-out runs/round_00/arithmetic_teacher/cocycle_audit/arithmetic_teacher_cocycle_report.json \
  --gamma-constraints-out runs/round_00/arithmetic_teacher/cocycle_audit/arithmetic_teacher_gamma_constraints.jsonl
```

Or run the full loop:

```bash
lean-rgc arithmetic-teacher-cocycle \
  --kernel-audit-rows runs/round_00/arithmetic_teacher/kernel_transition_audit/arithmetic_teacher_kernel_audit_rows.jsonl \
  --out runs/round_00/arithmetic_teacher/cocycle_audit \
  --compositions compositions.jsonl
```

## Pipeline integration

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v43_arith_cocycle \
  --dry-run \
  --arithmetic-teacher-graph \
  --arithmetic-teacher-kernel-audit \
  --arithmetic-teacher-cocycle-audit \
  --arithmetic-teacher-cocycle-max-auto-pairs 8
```

## Main artifacts

```text
arithmetic_teacher/cocycle_audit/arithmetic_teacher_transition_geometry.jsonl
arithmetic_teacher/cocycle_audit/arithmetic_teacher_transition_geometry_report.json
arithmetic_teacher/cocycle_audit/arithmetic_teacher_cocycle_rows.jsonl
arithmetic_teacher/cocycle_audit/arithmetic_teacher_cocycle_report.json
arithmetic_teacher/cocycle_audit/arithmetic_teacher_gamma_constraints.jsonl
arithmetic_teacher/cocycle_audit/arithmetic_teacher_gamma_constraints_report.json
arithmetic_teacher/cocycle_audit/arithmetic_teacher_cocycle_loop_report.json
```

## Status

The cocycle audit is a finite witness for teacher multiplicative consistency.  It is designed to
feed future Gamma/action-geometry loops, but it does not prove the full operation-stable teacher
quotient.
