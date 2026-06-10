# Lean-RGC v44: Gamma Transition Learner with Teacher Constraints

v44 adds a finite-chart Gamma transition learner.  It moves the old Gamma path
from a scalar/diagnostic audit toward an action-dependent affine propagation
model:

\[
D_{t+1} \approx B(a) + \Gamma(a)(D_t - R(a)).
\]

The learned objects remain finite audit charts, not canonical propagation
operators.

## New commands

### Learn action-dependent Gamma

```bash
lean-rgc gamma-transition-learner \
  --transitions runs/round_00/transitions.jsonl \
  --teacher-constraints runs/round_00/arithmetic_teacher/cocycle_audit/arithmetic_teacher_gamma_constraints.jsonl \
  --out runs/round_00/gamma_transition
```

Outputs:

```text
gamma_transition_model.json
gamma_transition_actions.jsonl
gamma_transition_audit_rows.jsonl
gamma_transition_action_geometry_patches.jsonl
gamma_transition_report.json
```

### Patch action geometry

```bash
lean-rgc gamma-transition-patch-action-geometry \
  --action-geometry runs/round_00/action_geometry/action_geometry.jsonl \
  --patches runs/round_00/gamma_transition/gamma_transition_action_geometry_patches.jsonl \
  --out runs/round_00/gamma_transition/action_geometry_gamma_patched.jsonl
```

## Pipeline integration

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v44_gamma \
  --dry-run \
  --gamma-transition-learner
```

If arithmetic teacher cocycle constraints exist, pipeline automatically uses:

```text
arithmetic_teacher/cocycle_audit/arithmetic_teacher_gamma_constraints.jsonl
```

To patch an existing action geometry registry in the same pipeline run, use:

```bash
--action-geometry --gamma-transition-learner --gamma-transition-patch-action-geometry
```

## Theory status

The learner fits action-local affine models:

```text
next_defect ≈ Gamma(action) @ residual_after_response + affine_bias(action)
```

with shrinkage toward a global Gamma model. Arithmetic teacher cocycle
constraints can regularize the scalar Gamma witness for matching action ids.

This is not a population-level Gamma proof. It is a finite chart used for tail
risk, action geometry, and future propagation audits.
