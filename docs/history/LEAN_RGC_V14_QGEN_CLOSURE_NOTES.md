# Lean-RGC v14: qgen closure hooks

v14 extends the v13 qgen loop from "generate candidate charts" to a more closed RGC loop:

```text
base audit responses
  -> qgen coker residual
  -> qgen defect registry
  -> qgen registry-guided candidates
  -> optional qgen registry audit / coker acceptance
  -> qgen carrier incidence patches
  -> optional carrier matrix merge
  -> carrier-safe action filtering
  -> next round merge
```

The generated objects remain witness/chart candidates.  They are not canonical proof objects; POMS promotion still requires parent non-payment, dual evidence, and least repair.

## New pipeline flags

```bash
--qgen-registry-candidates
--qgen-registry-max-candidates 64
--audit-qgen-registry-candidates
--qgen-registry-audit-max-actions 16
--qgen-registry-accept-coker
--qgen-registry-accept-margin 0.0
--qgen-registry-accept-max-per-task 16
--qgen-registry-accept-cost-weight 0.05
--qgen-registry-accept-carrier-weight 0.7
```

These turn `qgen/qgen_defect_registry.json` back into registry-guided proof-context candidates, optionally audit them, and optionally coker-accept them.

## New carrier matrix patch flags

```bash
--carrier-matrix-merge-qgen
--carrier-matrix-qgen-patch-weight 1.0
--carrier-matrix-qgen-require-safe
```

When both `--carrier-matrix` and `--carrier-matrix-merge-qgen` are enabled, `qgen/qgen_carrier_incidence.jsonl` is merged into the empirical carrier matrix before carrier-safe action filtering.  Outputs include:

```text
carrier_matrix.json
carrier_matrix_qgen.json
qgen_carrier_patch_report.json
multi_carrier_report.json
carrier_safe_actions.jsonl
```

## New standalone command

```bash
lean-rgc carrier-matrix-merge-patches \
  --matrix carrier_matrix.json \
  --patches qgen/qgen_carrier_incidence.jsonl \
  --out carrier_matrix_qgen.json \
  --report-out qgen_carrier_patch_report.json
```

## Iteration merge

`lean-rgc iterate` now passes the qgen registry and carrier-matrix closure flags to each pipeline round.  It also merges `qgen_registry_accepted_actions.jsonl` into the next round when present.  Raw `qgen_registry_candidates.jsonl` is merged only when `--qgen-merge-actions` is explicitly set.

## Minimal example

```bash
lean-rgc iterate \
  --tasks examples/minimal_theorems.jsonl \
  --actions examples/core_tactics.jsonl \
  --out runs/v14_qgen_closure \
  --dry-run \
  --rounds 2 \
  --max-actions 8 \
  --import-mode core \
  --qgen \
  --qgen-registry-candidates \
  --audit-qgen-registry-candidates \
  --qgen-registry-accept-coker \
  --carrier-matrix \
  --carrier-matrix-merge-qgen \
  --qgen-merge-actions
```

## Tests

v14 adds `tests/test_v14_qgen_closure.py`.  Full test suite status at packaging:

```text
43 passed
```
