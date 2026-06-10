# Lean-RGC v40: Defect Ontology Lifecycle

v40 adds a round-to-round lifecycle layer for mined defect atoms.  It takes the
v39 reconciliation output and combines it with POMS promotion evidence,
validation rows, and split suggestions to classify candidate atoms as merge
validated, novel pending, validated novel, shadow pending, open pending, split
proposed, and related lifecycle states.

The lifecycle output is intentionally not canonical.  It is a finite audit and
provenance chart.  Promotion to canonical status still requires parent non-paid
evidence, a dual certificate, and least-repair evidence.

Main CLI:

```bash
lean-rgc defect-ontology-lifecycle \
  --run-dir runs/my_run \
  --out runs/my_run/defect_ontology_lifecycle
```

Outputs:

- `defect_ontology_lifecycle_rows.jsonl`
- `defect_ontology_validated_atoms.jsonl`
- `defect_ontology_deprecations.jsonl`
- `defect_ontology_merge_decisions.jsonl`
- `defect_ontology_split_decisions.jsonl`
- `defect_registry_lifecycle.json`
- `defect_ontology_lifecycle_report.json`

This closes the first loop:

```
qgen/qcoord/carrier-quotient atoms
  -> ontology reconciliation
  -> POMS/validation evidence
  -> lifecycle status
  -> lifecycle registry
```
