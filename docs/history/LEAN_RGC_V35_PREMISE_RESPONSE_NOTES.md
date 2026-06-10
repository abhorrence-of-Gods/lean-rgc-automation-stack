# Lean-RGC v35: Premise Response Quotient Retrieval

v35 introduces a response-quotient layer for premise retrieval.

The key shift is:

```text
semantic / lexical premise similarity -> candidate pool only
premise-use response / carrier embedding -> selector
```

A premise is not treated as a primitive theorem name.  A premise-use context is

```text
u = (premise, use_mode, instantiation)
```

with use modes such as `exact`, `apply`, `rw`, and `simp`.  The registry stores
finite audited embeddings:

```text
E_prem(u) = (R(u), C(u), cost(u), uncertainty(u))
```

where `R(u)` is the response embedding and `C(u)` is carrier response.

## New commands

Build a premise response registry from audited premise candidates:

```bash
lean-rgc premise-response-registry \
  --responses runs/round_00/premise_audit/responses.jsonl \
  --actions runs/round_00/premise_actions.jsonl \
  --out runs/round_00/premise_response/premise_response_registry.jsonl \
  --summary-out runs/round_00/premise_response/premise_response_registry_summary.json
```

Retrieve premise-use candidates by coker / carrier normals:

```bash
lean-rgc premise-response-retrieve \
  --registry runs/round_00/premise_response/premise_response_registry.jsonl \
  --response-normal '{"goal.eq": 1.0}' \
  --carrier-normal '{"missing_simp_lemma": 0.5}' \
  --out runs/round_00/premise_response/premise_response_retrieved.jsonl \
  --out-actions runs/round_00/premise_response_actions.jsonl
```

Mine finite premise-use quotient classes:

```bash
lean-rgc premise-quotient-mine \
  --registry runs/round_00/premise_response/premise_response_registry.jsonl \
  --out runs/round_00/premise_response/premise_quotient
```

## Pipeline integration

When premise candidates are audited, pass:

```bash
--premise-index \
--audit-premise-candidates \
--premise-response-registry \
--premise-response-retrieve \
--premise-quotient-mine \
--audit-premise-response-candidates
```

The pipeline will create:

```text
premise_response/premise_response_registry.jsonl
premise_response/premise_response_retrieved.jsonl
premise_response/premise_quotient/premise_quotient_classes.jsonl
premise_response_actions.jsonl
premise_response_audit/responses.jsonl
```

## Status

These outputs are finite audit charts.  They are not canonical premise objects.
Canonical promotion requires parent non-payment, a dual certificate, and least repair.
