# Lean-RGC v50 Premise Contextual Quotient Notes

v50 implements the third premise-retrieval stage: premise-use contexts are no
longer grouped only by identity-context response.  They are wrapped in finite
safe pre/post contexts and quotiented by contextual response fingerprints.

## Core Object

The primitive is:

```text
u = (premise, use_mode, instantiation)
```

The contextual probe action is:

```text
g -> B(g) -> u(B(g)) -> A(u(B(g)))
```

and the baseline path is:

```text
g -> B(g) -> A(B(g)).
```

The fingerprint uses the incremental response:

```text
R^{A,B}(u; g) = response(B; u; A) - response(B; A).
```

For the existing audit schema, `response` is a defect-reduction chart
`delta(before) - delta(after)`, so this subtraction gives
`delta(g_AB) - delta(g_ABu)`.

## New Module

`lean_rgc/premise_contextual_quotient.py` exposes:

```python
generate_premise_contextual_candidates(...)
build_premise_contextual_fingerprints(...)
mine_premise_contextual_quotient(...)
validate_premise_contextual_quotient(...)
retrieve_premise_quotient_classes(...)
```

It also includes `premise_quotient_retrieved_actions(...)` for emitting
candidate actions from retrieved quotient classes.

## CLI

Standalone commands:

```bash
lean-rgc premise-contextual-generate
lean-rgc premise-contextual-fingerprints
lean-rgc premise-contextual-mine
lean-rgc premise-contextual-validate
lean-rgc premise-quotient-retrieve
```

Pipeline flags:

```bash
--premise-contextual-quotient
--premise-contextual-generate
--audit-premise-contextual-candidates
--premise-contextual-mine
--premise-contextual-validate
--premise-quotient-retrieve
```

`--premise-contextual-quotient` is a convenience flag for generation, audit,
fingerprint construction, mining, and validation.  Retrieval remains explicit
through `--premise-quotient-retrieve`.

## Artifacts

```text
premise_contextual_candidates.jsonl
premise_contextual_audit/responses.jsonl
premise_contextual_fingerprints.jsonl
premise_quotient_classes.jsonl
premise_quotient_members.jsonl
premise_quotient_representatives.jsonl
premise_quotient_validation_rows.jsonl
premise_quotient_validation_report.json
premise_quotient_retrieved_actions.jsonl
```

## Status

The implementation is a finite contextual probe chart.  It records domain
support, statuses, response/carrier/gamma/cost/audit summaries, heldout
validation rows, and quotient-class retrieval metadata.  It does not declare
canonical premise classes; classes remain
`not_canonical_parent_nonpaid_least_repair_required` until POMS evidence is
provided.

## Verification

Added `tests/test_v50_premise_contextual_quotient.py` covering:

- candidate and baseline generation;
- baseline-subtracted contextual fingerprints;
- finite quotient mining;
- heldout validation rows/report;
- quotient-class retrieval and emitted candidate actions;
- CLI command paths.
