# Lean-RGC v19: POMS Promotion Calculus

v19 adds an explicit POMS promotion layer above the qgen witness / acceptance / realized-response loop.

The key rule is conservative:

```text
canonical promotion = parent non-paid + dual certificate + least repair + explicit declaration / doctrine review
```

Finite qgen evidence remains a witness unless explicit POMS evidence is supplied.

## New / strengthened CLI

```bash
lean-rgc poms-promote \
  --run-dir runs/qgen_loop \
  --poms-rows runs/qgen_loop/poms_status_rows.jsonl \
  --evidence parent_certificates.jsonl \
  --out-json runs/qgen_loop/poms_promotion_report.json \
  --out-jsonl runs/qgen_loop/poms_promotion_rows.jsonl \
  --out-promoted-actions runs/qgen_loop/poms_promoted_actions.jsonl
```

Optional global flags for experiments:

```bash
--parent-nonpaid
--dual-certificate
--least-repair
--declare-canonical
```

These are intentionally explicit; canonical declarations should not be inferred from finite coker margin alone.

## Iterate integration

`lean-rgc iterate` already supports:

```bash
--poms-promote
--poms-promotion-evidence certs.jsonl
--poms-promote-parent-nonpaid
--poms-promote-dual-certificate
--poms-promote-least-repair
--poms-declare-canonical
```

When enabled, it writes:

```text
poms_promotion_report.json
poms_promotion_rows.jsonl
poms_promotion_rows.csv
poms_promoted_actions.jsonl
```

## Statuses

Typical statuses:

```text
witness_candidate
accepted_witness
paid_witness
open_parent_obstruction
forced_candidate
canonical_candidate
canonical_observable
witness_only_parent_paid
```

`canonical_observable` is only emitted when `--declare-canonical` and the required evidence is supplied.

## Theory mapping

- `poms_status`: finite qgen / carrier / realized-response witness ledger.
- `poms_promotion`: applies CanObsNS no-premature-refinement rule.
- `poms_promoted_actions`: actions whose parent evidence makes them forced/canonical candidates for a follow-up round.

This is still a finite audit chart, not a formal Lean proof of canonicality.
