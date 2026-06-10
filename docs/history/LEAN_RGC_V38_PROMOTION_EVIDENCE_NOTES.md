# Lean-RGC v38: Promotion Evidence Generator

v38 adds a conservative POMS promotion-evidence generator.

The prior POMS promotion calculus could consume external evidence rows such as
`parent_nonpaid`, `dual_certificate`, and `least_repair`, but the evidence had to be supplied manually.
This version mines finite audit/coker artifacts and writes evidence rows consumable by `poms-promote`.

## CLI

```bash
lean-rgc poms-evidence \
  --run-dir runs/my_run \
  --out-json runs/my_run/promotion_evidence_report.json \
  --out-jsonl runs/my_run/promotion_evidence_rows.jsonl \
  --out-poms runs/my_run/promotion_evidence_for_poms.jsonl
```

`promotion_evidence_for_poms.jsonl` can be passed directly to:

```bash
lean-rgc poms-promote \
  --run-dir runs/my_run \
  --evidence runs/my_run/promotion_evidence_for_poms.jsonl
```

## Iterate integration

```bash
lean-rgc iterate \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v38 \
  --dry-run \
  --rounds 1 \
  --qgen \
  --audit-qgen-candidates \
  --qgen-accept-coker \
  --poms-generate-evidence \
  --poms-promote
```

This writes:

- `promotion_evidence_report.json`
- `promotion_evidence_rows.jsonl`
- `promotion_evidence_for_poms.jsonl`
- `poms_promotion_report.json`
- `poms_promotion_rows.jsonl`

## Evidence sources

The generator mines:

- quotient-coordinate coker normal rows;
- carrier-quotient coker normal rows;
- qgen defect atoms;
- coker and robust-coker acceptance rows;
- audited qgen carrier-incidence patches;
- POMS status rows.

## Conservative status

The generated evidence is still finite-chart evidence.  It is not a canonical proof.  It is intended to automate the *inputs* to the existing POMS calculus:

```text
parent non-paid + dual certificate + least repair => canonical candidate
```

Canonical declaration still requires explicit downstream doctrine review, unless a caller separately passes `--declare-canonical` to `poms-promote`.
