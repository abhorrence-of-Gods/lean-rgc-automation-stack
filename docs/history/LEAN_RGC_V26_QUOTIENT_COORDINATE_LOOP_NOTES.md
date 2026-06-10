# Lean-RGC v26: Quotient Coordinate Loop

v26 connects quotient-coordinate generation to the main pipeline/iterate loop.

The key transition is:

```text
coker residual -> finite normal phi -> q_phi(d)=dot(phi,d)
```

rather than:

```text
residual coordinate -> defect label -> tactic template
```

## Added loop pieces

- `--quotient-coordinates` on `pipeline` and `iterate`.
- `--quotient-coordinate-validate` for finite holdout/over-refinement validation charts.
- `--audit-quotient-coordinate-candidates` to micro-audit candidate actions selected by quotient coordinates.
- `--quotient-coordinate-accept-coker` and `--quotient-coordinate-robust-coker-accept`.
- `--quotient-coordinate-registry-candidates` to expose quotient coordinates as registry readout charts for existing candidate generation.
- `--action-geometry-use-quotient-normals` to feed mined quotient-coordinate normals into action-geometry retrieval.

## Main artifacts

```text
quotient_coordinates/quotient_coordinates.jsonl
quotient_coordinates/state_coker_normals.jsonl
quotient_coordinates/quotient_coordinate_defect_registry.json
quotient_coordinates/quotient_coordinate_response_normal.json
quotient_coordinates/quotient_coordinate_validation_report.json
quotient_coordinate_audit/responses.jsonl
quotient_coordinate_accepted_actions.jsonl
quotient_coordinate_robust_accepted_actions.jsonl
```

## Status

All outputs are finite response-chart witnesses. They are not canonical observables.
Canonical promotion still requires parent non-paid + dual certificate + least repair.
