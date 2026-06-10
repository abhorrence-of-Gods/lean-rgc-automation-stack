# Lean-RGC v0.7 Notes

This version extends v0.6 with a more complete closed-loop path:

1. Registry-guided candidates can be micro-audited and then used to validate or demote mined defect atoms.
2. A lightweight premise index / retrieval chart is available for premise-carrier experiments.
3. Proof-state IR rows can be converted back into defect vectors, so structured IR can be used as a defect source.
4. The pipeline can optionally promote the mined defect registry after auditing registry candidates.

The implementation still treats tactic names, premise hits, proof-state strings, and generated candidate templates as charts/witnesses.  Promotion is evidence-based and finite-chart only; it is not a proof of canonicality.

## New commands

```bash
lean-rgc promote-registry \
  --registry runs/defect_registry.json \
  --audits runs/registry_audit/micro_audit.jsonl \
  --responses runs/registry_audit/responses.jsonl \
  --out runs/defect_registry.promoted.json \
  --report-out runs/defect_registry.promotion_report.json
```

```bash
lean-rgc build-premise-index \
  --tasks examples/core_theorems.jsonl \
  --actions runs/registry_candidates.jsonl \
  --out runs/premise_index.json
```

```bash
lean-rgc premise-retrieve \
  --index runs/premise_index.json \
  --tasks examples/core_theorems.jsonl \
  --out runs/premise_hits.jsonl \
  --k 8
```

```bash
lean-rgc premise-actions \
  --hits runs/premise_hits.jsonl \
  --out runs/premise_actions.jsonl
```

```bash
lean-rgc ir-defects \
  --ir runs/states_ir.jsonl \
  --out runs/ir_defects.jsonl
```

## v0.7 pipeline example

```bash
lean-rgc pipeline \
  --tasks examples/core_theorems.jsonl \
  --out runs/v7_core \
  --dry-run \
  --jobs 2 \
  --candidate-mode state \
  --max-actions 12 \
  --mine-defects \
  --registry-candidates \
  --audit-registry-candidates \
  --registry-audit-max-actions 8 \
  --promote-registry \
  --premise-index \
  --audit-premise-candidates \
  --premise-audit-max-actions 8 \
  --fit-gamma
```

## Remaining major work

- Persistent Lean worker / server integration.
- True structured proof-state extraction from Lean internals.
- Semantic Mathlib premise retrieval.
- Full coker-margin promotion beyond finite proxy metrics.
- Multi-carrier constrained proof search.
