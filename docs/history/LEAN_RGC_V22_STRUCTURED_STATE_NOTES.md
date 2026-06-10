# Lean-RGC v22: Structured State Extraction

v22 adds a stable structured proof-state schema on top of the v21 Lean Server Adapter.

The new object is a chart, not a canonical quotient:

```text
StructuredProofState = (
  GoalASTNode[],
  LocalContextGraph,
  MetaVarGraph,
  TypeclassObligationGraph,
  messages,
  extraction metadata
)
```

Current extraction is text-derived unless a future Lean worker returns kernel JSON.  The schema is deliberately shaped so the backend can later be replaced by Lean Expr / local context / metavariable data without changing downstream artifacts.

## New module

```text
lean_rgc/structured_state.py
```

## New CLI

```bash
lean-rgc structured-state-extract \
  --tasks tasks.jsonl \
  --audits audit/micro_audit.jsonl \
  --out structured_states.jsonl \
  --summary-out structured_state_summary.json
```

## Server integration

`server-audit` now writes `structured_states.jsonl` using the v22 schema.  Rows include:

- `schema_version = lean-rgc-structured-state-v22.0`
- `canonical_status = structured_state_chart_only_not_canonical`
- goal-level target head, relation, symbols, binders, carrier atoms
- local context nodes and dependency edges
- metavariable chart
- typeclass obligation chart

## Important status

This is not yet kernel-native AST extraction.  It is a stable bridge schema.  v23 should replace the text-derived backend with Lean worker supplied JSON for GoalAST, LocalContextGraph, MetaVarGraph, and TypeclassObligationGraph.
