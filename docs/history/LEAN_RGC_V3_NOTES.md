# Lean-RGC Automation Stack v0.3

This release advances the v0.2 scaffold toward larger Lean tactic experiments.

## New commands

### `lean-rgc candidates`
Generate state-dependent tactic candidates for a task file.

```bash
lean-rgc candidates --tasks examples/minimal_theorems.jsonl --out runs/candidates.jsonl
```

### `lean-rgc make-transitions`
Convert micro-audit response rows into finite-chart Gamma transition rows.

```bash
lean-rgc make-transitions --responses runs/audit/responses.jsonl --out runs/transitions.jsonl
```

### `lean-rgc dataset-summary`
Summarize response data: status counts, response norms, carrier delta, success/timeout rates.

```bash
lean-rgc dataset-summary --responses runs/audit/responses.jsonl --out runs/dataset_summary.json
```

### `lean-rgc split`
Train/validation split for JSONL datasets, optionally grouped by `state_id` or `task_id`.

```bash
lean-rgc split --input runs/audit/responses.jsonl --out runs/split --group-key state_id
```

### `lean-rgc carrier-accept`
Micro-audit generated carrier contexts and accept only those with positive carrier coker-margin proxy.

```bash
lean-rgc carrier-accept \
  --tasks examples/minimal_theorems.jsonl \
  --proposals runs/carrier_generated_contexts.jsonl \
  --out runs/carrier_acceptance.jsonl \
  --dry-run
```

### `lean-rgc report`
Collect the main run artifacts into one JSON report.

```bash
lean-rgc report --run-dir runs/my_run --out runs/my_run/final_report.json
```

### `lean-rgc pipeline`
Run the basic audit → response model → quotient → carrier coker/generator pipeline.

```bash
lean-rgc pipeline \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/tactic_templates.jsonl \
  --out runs/pipeline \
  --dry-run \
  --jobs 4
```

## New modules

- `lean_rgc.dataset`: dataset summaries, splits, transition conversion, run reports.
- `lean_rgc.carrier_acceptance`: generated carrier-context micro-audit and coker-margin acceptance.
- `lean_rgc.pipeline`: basic end-to-end pipeline helper.

## Design update

Carrier generation is now a two-step tower:

1. `carrier-generate` proposes contexts from carrier residual atoms.
2. `carrier-accept` micro-audits those contexts and accepts only if a carrier coker-margin proxy is positive after cost/audit debt.

Gamma remains audit-first. `make-transitions` + `gamma-audit` now form the minimal transition dataset loop. Gamma control should still wait until it beats persistence on held-out trajectories.

## Smoke-tested

- `pipeline` dry-run.
- `carrier-accept` dry-run.
- `make-transitions` + `gamma-audit`.
- `dataset-summary`, `split`, `report`.
- `pytest -q` passes.
