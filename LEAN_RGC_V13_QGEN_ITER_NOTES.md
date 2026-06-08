# Lean-RGC v13: qgen-in-the-loop integration

This revision connects the quotient-first generator (qgen) to the normal pipeline and iterative loop.

## New CLI surfaces

### Pipeline

`lean-rgc pipeline` now accepts:

- `--qgen`
- `--audit-qgen-candidates`
- `--qgen-audit-max-actions N`
- `--qgen-accept-coker`
- `--qgen-accept-margin X`
- `--qgen-accept-max-per-task N`
- `--qgen-accept-cost-weight X`
- `--qgen-accept-carrier-weight X`

When enabled, the pipeline now runs:

```text
base audit responses
  -> qgen residual/coker synthesis
  -> qgen_context_candidates.jsonl
  -> optional qgen micro-audit
  -> optional coker acceptance
  -> qgen_accepted_actions.jsonl
```

All qgen outputs are surfaced in `pipeline_summary.json` under `pipeline_files`.

### Iterate

`lean-rgc iterate` now forwards qgen options into each round and can merge qgen outputs into the next action set:

- `--qgen`
- `--qgen-merge-actions`
- `--audit-qgen-candidates`
- `--qgen-audit-max-actions N`
- `--qgen-accept-coker`
- `--qgen-accept-margin X`
- `--qgen-accept-max-per-task N`

The merge priority is:

1. audited qgen accepted actions at `round_xx/qgen_accepted_actions.jsonl`;
2. raw qgen accepted actions at `round_xx/qgen/qgen_accepted_actions.jsonl`;
3. raw qgen candidates only when `--qgen-merge-actions` is enabled.

## Canonicality status

Generated qgen objects remain candidate charts/witnesses. They are not canonical proof observables. They require Lean micro-audit and coker acceptance; canonical promotion still requires parent non-payment, a dual certificate, and least-repair status.

## Tests

The suite includes a dry-run qgen-audit-accept iterative test. Current status:

```text
41 passed
```
