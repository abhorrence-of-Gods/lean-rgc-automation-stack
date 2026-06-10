# Lean-RGC v17: qgen realized-response and carrier patch audit

v17 adds the next closure layer after v16 acceptance lineage.

## Additions

- `lean_rgc.realized_response.collect_qgen_realized_calibration`
- `lean-rgc qgen-realized-calibration`
- automatic `qgen_realized_calibration.json/csv` at the end of `iterate --qgen`
- iteration reports now include qgen acceptance lineage summaries and qgen robust acceptance summaries
- quality gates now surface qgen lineage / robust acceptance metrics when present
- `lean_rgc.carrier_patch_audit.audit_carrier_incidence_patches`
- `lean-rgc carrier-patch-audit`
- optional `--carrier-matrix-qgen-audit-patches` before qgen carrier-incidence patches are merged into the carrier matrix

## Status

All outputs are finite charts/witnesses.  They are not canonical proof objects.  They help detect whether qgen accepted actions and qgen carrier patches survive the next audit layer.

## Tests

`57 passed` in the v17 working tree.
