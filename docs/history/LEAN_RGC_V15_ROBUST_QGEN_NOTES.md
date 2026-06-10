# Lean-RGC v15: Robust qgen acceptance hooks

v15 adds a conservative robust-acceptance layer for qgen-generated proof contexts.

The core change is that qgen candidates can now be accepted using a shadow/robust
acceptance chart instead of only a single deterministic coker-margin proxy.  The
status remains witness-level: accepted actions are not canonical proof objects;
they are candidate contexts that passed a quotient/coker-oriented audit chart.

## New module

- `lean_rgc.robust_acceptance`
  - `robust_accept_candidate_rows(...)`
  - `robust_accept_candidates_file(...)`
  - `run_robust_acceptance(...)` compatibility wrapper for pipeline hooks

Robust acceptance compares primary candidate audit margins with an optional
shadow/held-out audit chart.  The robust margin is

```text
min(train_margin, shadow_margin) - disagreement_weight * |train - shadow|
```

If no shadow rows are provided, it falls back to ordinary primary-margin
acceptance but records the decision as a robust-acceptance chart, not as a
canonical promotion.

## New CLI

```bash
lean-rgc robust-accept \
  --base-responses audit/responses.jsonl \
  --candidate-responses qgen_audit/responses.jsonl \
  --out qgen_robust_acceptance_rows.jsonl \
  --report-out qgen_acceptance_report.json \
  --accepted-actions-out qgen_accepted_actions.jsonl
```

## Pipeline integration

`lean-rgc pipeline` now accepts:

```text
--qgen-robust-accept
--qgen-registry-robust-accept
--qgen-robust-z
--qgen-robust-min-repeats
--qgen-robust-min-success-rate
```

The last three are compatibility knobs for future LCB/repeated-audit robust
acceptance; the current implementation is shadow-margin robust acceptance.

## Iterate integration

`lean-rgc iterate` forwards the robust qgen flags to each round's pipeline.

## Tests

v15 adds:

```text
tests/test_v15_robust_acceptance.py
```

Full suite status:

```text
50 passed
```

## Theoretical status

This is a system-level hardening step for the qgen loop:

```text
coker residual -> qgen candidate -> audit -> robust acceptance -> next round
```

It does not implement canonical promotion.  Promotion still requires parent
non-payment, dual certificate, and least-repair logic.
