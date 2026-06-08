# Lean-RGC Automation Stack v0.2

This revision extends the initial scaffold with scale-oriented pieces:

- parallel/batch micro-audit (`batch-audit`)
- file-backed audit cache support
- structured Lean message parser (`state_parser.py`)
- finite response learner (`train-response`, `predict-response`)
- finite response-cone / carrier-coker projection (`carrier-coker`)
- carrier context proposal generation (`carrier-generate`)
- Gamma/trajectory audit primitives
- minimal Lake project template generator (`init-lake`)
- minimal RGC trajectory/search runner (`run-search`)

## Recommended first run

```bash
lean-rgc batch-audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/tactic_templates.jsonl \
  --out runs/batch_dry \
  --dry-run \
  --jobs 4 \
  --max-actions 8

lean-rgc train-response \
  --responses runs/batch_dry/responses.jsonl \
  --actions examples/tactic_templates.jsonl \
  --out runs/batch_dry/response_model.json

lean-rgc carrier-coker \
  --defects runs/batch_dry/defects.jsonl \
  --actions examples/tactic_templates.jsonl \
  --out runs/batch_dry/carrier_coker.json
```

## Real Lean audit

Use `lean-rgc init-lake --out lean_playground --no-mathlib` for a tiny Lean project, or omit `--no-mathlib` for a Mathlib project. Then run with:

```bash
lean-rgc batch-audit \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/tactic_templates.jsonl \
  --out runs/lean_audit \
  --workdir /path/to/lake/project \
  --lean-cmd "lake env lean" \
  --jobs 4
```

## Status

This is still a finite-chart automation scaffold. Tactic labels, goal strings, and clusters are not canonical objects. They are witnesses/charts for response and carrier quotients.
