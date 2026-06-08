# Lean-RGC v15: Robust coker acceptance and qgen lineage

This revision adds a held-out/robust coker acceptance layer.

## New command

```bash
lean-rgc robust-coker-accept \
  --base-responses audit/responses.jsonl \
  --candidate-responses qgen_audit/responses.jsonl \
  --out-report qgen_robust_acceptance_report.json \
  --out-actions qgen_robust_accepted_actions.jsonl \
  --out-rows qgen_robust_acceptance_rows.jsonl
```

The command splits base responses by state into train and holdout cones.  Candidate
margin is computed against the train residual normal, but the support baseline is
`max(train_support, holdout_support)`.  This makes coker acceptance less sensitive
to stage overfit.

## Status

Robust coker acceptance is still a finite chart/witness.  It is not canonical
promotion.  Promotion still requires parent non-payment, dual evidence, and least
repair.

## qgen lineage

qgen-generated actions and defect atoms now carry lightweight lineage/provenance
metadata so later rounds can trace a candidate back to a coker residual chart.
