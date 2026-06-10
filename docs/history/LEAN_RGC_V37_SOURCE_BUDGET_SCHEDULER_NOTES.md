# Lean-RGC v37: Source-budget active audit scheduler

v37 adds a cross-source audit budget allocator.  Earlier `--audit-scheduler`
ranked candidates inside a single candidate JSONL before an audit stage.  This
is useful, but it does not decide how to allocate a fixed audit budget across
candidate families such as qgen, action geometry, quotient coordinates, carrier
quotient, contextual probes, registry, premise response, and IR candidates.

The new layer treats audit scheduling as a finite chart-level allocation problem:

```text
candidate sources -> scored candidates -> source-budget allocation -> selected audit batch
```

The output is not canonical.  It is an audit-budget chart/witness.  It should be
read as a finite approximation to expected coker margin per audit cost, not as a
proof that a candidate family is canonical.

## Standalone command

```bash
lean-rgc source-budget-schedule \
  --candidates qgen=round_00/qgen/qgen_context_candidates.jsonl \
  --candidates action_geometry=round_00/action_geometry/action_geometry_candidates.jsonl \
  --run-dir round_00 \
  --out-actions round_00/source_budget/source_budget_actions.jsonl \
  --out-rows round_00/source_budget/source_budget_rows.jsonl \
  --out-report round_00/source_budget/source_budget_report.json \
  --budget 64 \
  --min-per-source 1
```

`--candidates` accepts either `PATH` or `SOURCE=PATH`.  `--source` is kept as a
backward-compatible alias.  `--run-dir` discovers common candidate files under a
run directory.

## Pipeline integration

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v37_source_budget \
  --dry-run \
  --qgen \
  --action-geometry \
  --action-geometry-retrieve \
  --carrier-quotient \
  --source-budget \
  --audit-source-budget-candidates \
  --source-budget-budget 32
```

This writes:

```text
source_budget/source_budget_actions.jsonl
source_budget/source_budget_rows.jsonl
source_budget/source_budget_report.json
source_budget_audit/responses.jsonl        # if --audit-source-budget-candidates
source_budget_action_report.json           # if audited
```

## Scoring

Each candidate receives an active-audit scheduler score using response/coker
signals, carrier signals, uncertainty, novelty, prior success, timeout risk, and
cost.  The source scheduler then allocates a global budget across sources with
source quotas and a greedy cross-source fairness penalty.

Important knobs:

```text
--source-budget-budget
--source-budget-min-per-source
--source-budget-max-per-source
--source-budget-per-task-cap
--source-budget-per-action-cap
--source-budget-coker-weight
--source-budget-carrier-weight
--source-budget-uncertainty-weight
--source-budget-novelty-weight
--source-budget-success-weight
--source-budget-cost-weight
--source-budget-timeout-weight
```

## Status

The scheduler output has canonical status:

```text
source_budget_scheduler_is_audit_budget_chart_not_canonical
```

It is a budget-allocation chart, not a canonical observable or a forced proof
context.  Candidate families selected by the scheduler still require audit,
robust acceptance, lineage tracking, and POMS promotion if they are ever to be
considered forced/canonical.
