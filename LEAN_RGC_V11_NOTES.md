# Lean-RGC v0.11 Notes

v0.11 adds failure-signature mining as a new chart between micro-audit failures and carrier/registry candidate generation.

## New commands

```bash
lean-rgc failure-signatures \
  --audits runs/audit/micro_audit.jsonl \
  --responses runs/audit/responses.jsonl \
  --out runs/failure_signatures.jsonl \
  --actions-out runs/failure_signature_actions.jsonl
```

Pipeline integration:

```bash
lean-rgc pipeline \
  ... \
  --failure-signatures \
  --audit-failure-signature-candidates \
  --failure-signature-accept-coker
```

Iteration integration:

```bash
lean-rgc iterate \
  ... \
  --failure-signatures \
  --audit-failure-signature-candidates \
  --failure-signature-accept-coker
```

## Meaning

Failure signatures are not canonical defects. They are finite audit charts that group repeated Lean failure patterns, attach likely carrier atoms, and emit candidate proof contexts. Candidates must still be micro-audited and accepted by finite coker-margin proxy before entering the next action universe.

Typical signatures include:

- `rfl_before_intro`
- `unintroduced_binder`
- `unsplit_and_target`
- `and_hyp_projection_needed`
- `typeclass_synthesis_failure`
- `unknown_identifier_or_missing_premise`
- `arith_backend_needed`
- `partial_progress_tail`

## RGC position

v0.11 extends the loop:

```text
audit failure -> failure signature -> candidate tactics -> micro-audit -> coker acceptance -> next-round actions
```

This is a pragmatic bridge toward automatic defect discovery. It is still a chart/witness layer, not a canonical defect registry by itself.
