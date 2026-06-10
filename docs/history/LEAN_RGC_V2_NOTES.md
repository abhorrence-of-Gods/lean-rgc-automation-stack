# Lean-RGC Automation Stack v0.2

This release moves the scaffold beyond one-shot micro-audits.

New / stabilized pieces:

1. File-mode proof-state parsing with `LeanMessageParser` and partial-success flags.
2. Response learner CLI (`train-response`, `predict-response`) using conservative action/class means and LCB predictions.
3. Carrier-coker proxy (`carrier-coker`) for finite carrier residual auditing.
4. RGC guided short trajectory search (`run-search`) with carrier constraints and optional response model.
5. Lake project template generation (`init-lake`) for real Lean/Lake experiments.

Recommended smoke sequence:

```bash
lean-rgc audit --tasks examples/minimal_theorems.jsonl --actions examples/tactic_templates.jsonl --out runs/audit --dry-run
lean-rgc train-response --responses runs/audit/responses.jsonl --actions examples/tactic_templates.jsonl --out runs/resp_model.json
lean-rgc quotient --responses runs/audit/responses.jsonl --out runs/components.jsonl
lean-rgc carrier-generate --defects runs/audit/defects.jsonl --out runs/carrier_generated.jsonl
lean-rgc carrier-coker --defects runs/audit/defects.jsonl --actions examples/tactic_templates.jsonl --out runs/carrier_coker.jsonl
lean-rgc run-search --tasks examples/minimal_theorems.jsonl --out runs/search --response-model runs/resp_model.json --dry-run --carrier-budget 10
lean-rgc init-lake --out runs/lake_template --no-mathlib
```

The dry-run search is only a pipeline check. For real Lean data, create a Lake project and run with `--workdir /path/to/project --lean-cmd "lake env lean"`.

Design invariant: tactic labels remain charts. The primitive object is the response quotient / carrier quotient, not the tactic name.
