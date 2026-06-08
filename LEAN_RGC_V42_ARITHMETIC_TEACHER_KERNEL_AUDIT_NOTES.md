# Lean-RGC v42: Arithmetic Teacher Kernel Transition Audit

v42 connects arithmetic teacher graph transformations to the Lean server adapter so that teacher constraints can be checked as goal-state transition witnesses rather than only text-chart matches.

## New command

```bash
lean-rgc arithmetic-teacher-kernel-audit \
  --transformations runs/round_00/arithmetic_teacher/arithmetic_teacher_transformations.jsonl \
  --tasks examples/minimal_theorems.jsonl \
  --structured-states runs/round_00/audit/structured_states.jsonl \
  --out runs/round_00/arithmetic_teacher/kernel_transition_audit \
  --server-backend native
```

For CI or environments without Lean:

```bash
lean-rgc arithmetic-teacher-kernel-audit \
  --transformations .../arithmetic_teacher_transformations.jsonl \
  --tasks examples/minimal_theorems.jsonl \
  --out .../kernel_transition_audit \
  --dry-run \
  --server-backend dry_run
```

## Pipeline integration

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v42 \
  --arithmetic-teacher-graph \
  --arithmetic-teacher-kernel-audit \
  --server-backend native
```

The pipeline writes:

```text
arithmetic_teacher/kernel_transition_audit/arithmetic_teacher_kernel_actions.jsonl
arithmetic_teacher/kernel_transition_audit/arithmetic_teacher_kernel_micro_audit.jsonl
arithmetic_teacher/kernel_transition_audit/arithmetic_teacher_kernel_responses.jsonl
arithmetic_teacher/kernel_transition_audit/arithmetic_teacher_kernel_structured_states.jsonl
arithmetic_teacher/kernel_transition_audit/arithmetic_teacher_kernel_audit_rows.jsonl
arithmetic_teacher/kernel_transition_audit/arithmetic_teacher_kernel_audit_report.json
```

## Status

This is still a finite transition witness, not a canonical teacher quotient. With the current source-check/native backend, the audit can verify theorem candidate checking and return kernel-shaped state payloads where available. Full in-memory `MVarId` tactic-state mutation remains future work.

