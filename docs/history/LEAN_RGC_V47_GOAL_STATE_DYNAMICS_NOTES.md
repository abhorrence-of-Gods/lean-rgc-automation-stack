# Lean-RGC v47: Goal-State Dynamics Substrate

v47 adds a first-class goal-state dynamics layer:

- `ExprGraph` chart extraction from kernel-shaped payloads
- `LocalDeclGraph` chart extraction
- `MetavariableGraph` chart extraction and a proof-progress measure
- `TypeclassGraph` chart extraction
- before/after kernel-state side channels in persistent/server audit records
- transition deltas for `g --a--> g'`

This is still a finite chart and not a canonical proof-state quotient.  A true Lean kernel RPC worker can fill the same schema with real Expr / LocalDecl / MVar / typeclass objects.

## CLI

```bash
lean-rgc goal-state-transitions \
  --audits runs/round_00/audit/micro_audit.jsonl \
  --out runs/round_00/audit/goal_state_transitions.jsonl \
  --summary-out runs/round_00/audit/goal_state_transition_report.json
```

```bash
lean-rgc kernel-state-graphs \
  --kernel-jsonl kernel_states.jsonl \
  --out goal_state_graphs.jsonl
```

## Theory

The primitive observation becomes

```text
g --a--> g'
```

with response

```text
R(a;g) = delta(g) - delta(g')
```

and MVar response

```text
mu(M_g) - mu(M_g')
```

rather than tactic success/failure or goal text differences.
