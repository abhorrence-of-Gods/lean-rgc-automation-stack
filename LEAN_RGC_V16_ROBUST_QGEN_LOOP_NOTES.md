# Lean-RGC v16: robust qgen loop integration

v16 wires the v15 held-out robust coker acceptor into the `pipeline` and `iterate` qgen loop.

The status remains witness/chart-level: robust coker acceptance is a stronger finite-audit acceptance certificate, not canonical promotion. Canonical promotion still requires parent non-payment, a dual certificate, and least repair.

## New pipeline / iterate flags

```bash
--qgen-robust-coker-accept
--qgen-registry-robust-coker-accept
--qgen-robust-coker-holdout-fraction 0.35
--qgen-robust-coker-uncertainty-weight 0.10
--qgen-robust-coker-carrier-gain-weight 0.25
--qgen-robust-coker-audit-penalty 1.0
--qgen-robust-coker-require-success
```

Use these together with the existing qgen audit and coker flags, for example:

```bash
lean-rgc iterate \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v16_qgen_robust \
  --dry-run \
  --rounds 2 \
  --max-actions 8 \
  --import-mode core \
  --qgen \
  --audit-qgen-candidates \
  --qgen-accept-coker \
  --qgen-robust-coker-accept
```

For qgen registry candidates:

```bash
lean-rgc iterate \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v16_qgen_registry_robust \
  --dry-run \
  --rounds 2 \
  --qgen \
  --qgen-registry-candidates \
  --audit-qgen-registry-candidates \
  --qgen-registry-accept-coker \
  --qgen-registry-robust-coker-accept
```

## New artifacts

For direct qgen candidates:

```text
qgen_robust_acceptance_report.json
qgen_robust_acceptance_rows.jsonl
qgen_robust_acceptance_rows.csv
qgen_robust_accepted_actions.jsonl
```

For qgen registry candidates:

```text
qgen_registry_robust_acceptance_report.json
qgen_registry_robust_acceptance_rows.jsonl
qgen_registry_robust_acceptance_rows.csv
qgen_registry_robust_accepted_actions.jsonl
```

The legacy accepted-action filenames are also populated for compatibility:

```text
qgen_accepted_actions.jsonl
qgen_registry_accepted_actions.jsonl
```

## Iterate merge priority

`iterate` now merges robust qgen accepted actions first:

```text
qgen_robust_accepted_actions.jsonl
qgen_registry_robust_accepted_actions.jsonl
qgen_accepted_actions.jsonl
qgen_registry_accepted_actions.jsonl
raw qgen candidates only if --qgen-merge-actions
```

This makes the default qgen loop prefer held-out robust witnesses over ordinary finite coker witnesses.

## Tests

v16 adds `tests/test_v16_qgen_robust_loop.py`.

Current result:

```text
54 passed
```
