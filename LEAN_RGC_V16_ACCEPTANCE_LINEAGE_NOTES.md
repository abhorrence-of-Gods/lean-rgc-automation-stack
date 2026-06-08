# Lean-RGC v16: qgen acceptance lineage

v16 adds a provenance layer that links qgen coker residuals to generated contexts, micro-audit rows, coker/robust acceptance records, and accepted actions.

## New command

```bash
lean-rgc qgen-acceptance-lineage \
  --qgen-dir runs/round_00/qgen \
  --audit-responses runs/round_00/qgen_audit/responses.jsonl \
  --acceptance-rows runs/round_00/qgen_acceptance_rows.jsonl \
  --accepted-actions runs/round_00/qgen_accepted_actions.jsonl \
  --registry-candidates runs/round_00/qgen_registry_candidates.jsonl \
  --out runs/round_00/qgen_acceptance_lineage.json
```

## Pipeline integration

When `--qgen` is enabled, `pipeline` now writes:

```text
qgen_acceptance_lineage.json
```

The graph includes:

- finite coker projection node,
- qgen defect atom candidates,
- qgen context candidates,
- qgen registry readouts,
- micro-audit response nodes,
- coker / robust-coker acceptance records,
- accepted context nodes.

This is still a finite chart/witness graph, not a canonical proof object. Canonical promotion still requires parent non-paid + dual certificate + least repair.
