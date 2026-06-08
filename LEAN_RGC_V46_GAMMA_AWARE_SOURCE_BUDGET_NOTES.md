# Lean-RGC v46: Gamma-aware Source Budget Scheduler

v46 connects learned finite-chart Gamma propagation signals to the source-budget
active audit scheduler.

Earlier stages can generate many candidate families:

- qgen
- action geometry
- quotient coordinates
- carrier quotient
- premise response
- contextual probes

v37 allocated audit budget across these sources using response, carrier,
uncertainty, novelty, success, and cost scores.  v46 adds a Gamma-aware
correction so the scheduler can prefer source families whose candidates are not
only locally useful but also tail-stable.

The adjustment is finite-chart evidence only.  It is not a canonical propagation
operator.

## Score adjustment

For a candidate action, the scheduler reads Gamma-aware metadata when present:

```text
gamma_tail_value_gain = gamma_tail_response_score - local_response_score
gamma_tail_risk       = TailRisk(Gamma(a))
```

and adjusts the source-budget score by

```text
Delta score = gamma_value_weight * gamma_tail_value_gain
              - gamma_tail_risk_weight * gamma_tail_risk
```

The selected candidate metadata records the Gamma-aware score components under
`metadata.source_budget_scheduler`.

## CLI usage

```bash
lean-rgc source-budget-schedule \
  --run-dir runs/round_00 \
  --out-actions runs/round_00/source_budget/source_budget_actions.jsonl \
  --out-rows runs/round_00/source_budget/source_budget_rows.jsonl \
  --out-report runs/round_00/source_budget/source_budget_report.json \
  --gamma-aware \
  --gamma-value-weight 1.0 \
  --gamma-tail-risk-weight 0.5
```

Pipeline / iterate flags:

```bash
--source-budget
--source-budget-gamma-aware
--source-budget-gamma-value-weight 1.0
--source-budget-gamma-tail-risk-weight 0.5
```

A typical pipeline:

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v46_gamma_source_budget \
  --dry-run \
  --qgen \
  --action-geometry \
  --action-geometry-retrieve \
  --action-geometry-use-qgen-normals \
  --action-geometry-use-gamma-transition \
  --action-geometry-gamma-aware \
  --source-budget \
  --source-budget-gamma-aware \
  --audit-source-budget-candidates
```

## Outputs

`source_budget/source_budget_report.json` now includes:

```json
"gamma_aware": true,
"gamma_summary": {
  "gamma_aware": true,
  "n_adjusted": 12,
  "mean_tail_value_gain": 0.03,
  "mean_tail_risk": 0.01
}
```

`source_budget/source_budget_rows.jsonl` rows include Gamma scoring terms.

## Status

This stage is an audit-budget allocation chart.  It does not make Gamma
canonical.  Canonical promotion still requires parent non-payment, dual
certificate, and least-repair evidence.
