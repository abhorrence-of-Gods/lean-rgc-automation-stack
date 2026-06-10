# Lean-RGC v39: Defect Ontology Reconciliation

v39 adds a finite-chart reconciliation layer for mined defect atoms.

It compares qgen / quotient-coordinate / carrier-quotient defect atom candidates against an existing registry and classifies each candidate as:

- `merge`: likely the same coordinate as an existing atom;
- `shadow`: quotient-respecting readout / weaker shadow of an existing atom;
- `novel`: low similarity candidate atom;
- `open`: ambiguous, needs more audit;
- `existing_update`: same atom id, evidence update.

It also emits split suggestions when multiple low-mutual-similarity candidates map to the same existing atom.

This remains a finite chart / witness layer, not canonical ontology promotion.
Canonical status still requires parent non-paid evidence, a dual certificate, and least repair.

## CLI

```bash
lean-rgc defect-ontology-reconcile \
  --run-dir runs/my_run \
  --base-registry registry.json \
  --out runs/my_run/defect_ontology
```

Outputs:

- `defect_ontology_report.json`
- `defect_ontology_rows.jsonl`
- `defect_ontology_merge_map.jsonl`
- `defect_ontology_split_suggestions.jsonl`
- `defect_registry_reconciled.json`
