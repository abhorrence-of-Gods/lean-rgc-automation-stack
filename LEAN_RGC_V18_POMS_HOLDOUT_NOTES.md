# Lean-RGC v18: POMS Status + Held-out Carrier Patch Audit

This revision adds a conservative status layer for qgen artifacts and a stricter carrier-patch audit mode.

## New CLI

### POMS status

```bash
lean-rgc poms-status \
  --run-dir runs/qgen_loop \
  --out-json runs/qgen_loop/poms_status_report.json \
  --out-jsonl runs/qgen_loop/poms_status_rows.jsonl \
  --out-csv runs/qgen_loop/poms_status_rows.csv
```

The output classifies qgen artifacts as finite POMS witnesses, for example:

- `witness_candidate`
- `accepted_witness`
- `paid_witness`
- `carrier_patch_witness`
- `paid_carrier_patch_witness`
- `open_carrier_patch_candidate`

No output is marked canonical.  Canonical promotion still requires parent-non-paid + dual certificate + least repair.

### Held-out carrier patch audit

```bash
lean-rgc carrier-patch-audit \
  --patches round_00/qgen/qgen_carrier_incidence.jsonl \
  --responses round_00/qgen_audit/responses.jsonl \
  --holdout-fraction 0.35 \
  --require-heldout \
  --out-report round_00/qgen_carrier_patch_audit_report.json \
  --out-patches round_00/qgen_carrier_incidence_audited.jsonl
```

This splits audit rows by stable hash and accepts a patch only if the pooled/train audit passes, and if `--require-heldout` is set, the held-out audit also passes.

## Pipeline / iterate options

The existing qgen carrier patch audit now accepts:

```bash
--carrier-matrix-qgen-patch-holdout-fraction 0.35
--carrier-matrix-qgen-patch-require-heldout
```

Example:

```bash
lean-rgc iterate \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v18_qgen_poms \
  --dry-run \
  --rounds 2 \
  --qgen \
  --audit-qgen-candidates \
  --qgen-accept-coker \
  --qgen-robust-coker-accept \
  --carrier-matrix \
  --carrier-matrix-merge-qgen \
  --carrier-matrix-qgen-audit-patches \
  --carrier-matrix-qgen-patch-holdout-fraction 0.35 \
  --carrier-matrix-qgen-patch-require-heldout
```

At the end of `iterate`, if qgen lineage or realized-response files exist, the run now also writes:

- `poms_status_report.json`
- `poms_status_rows.jsonl`
- `poms_status_rows.csv`

## Quality gates

`lean-rgc quality-gates` now accepts qgen-specific thresholds:

```bash
--min-qgen-realized-match-rate 0.5
--min-qgen-realized-success-rate 0.5
--min-qgen-realized-goal-response 0.0
--min-qgen-patch-audit-accept-rate 0.1
```

These are still finite chart quality checks, not canonicality tests.
